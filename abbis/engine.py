"""Core ABBIS Lite analytics. Raw CSVs are never modified."""
from __future__ import annotations

from pathlib import Path
import hashlib
import math
import re
import sqlite3
from typing import Any

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
LOCAL_DIR = Path(__file__).resolve().parents[1] / "data" / "local"
BLOOD_GROUPS = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
COMPONENTS = ["RBC", "WB", "PLT", "FFP", "CRYO"]


def load_frames(data_dir: str | Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load all starter tables and parse dates. Never write back to raw files."""
    p = Path(data_dir)
    names = {
        "facilities": "facilities.csv", "units": "units.csv", "requests": "requests.csv",
        "stock": "daily_stock.csv", "transfers": "transfers.csv", "temps": "temperature_logs.csv",
        "donors": "donors.csv", "donations": "donations.csv", "outages": "power_outages.csv",
        "routes": "routes.csv",
    }
    frames = {key: pd.read_csv(p / filename, low_memory=False) for key, filename in names.items()}
    for col in ["date"]:
        frames["stock"][col] = pd.to_datetime(frames["stock"][col], errors="coerce")
    for col in ["requested_at", "last_unit_available_at"]:
        frames["requests"][col] = pd.to_datetime(frames["requests"][col], errors="coerce")
    frames["temps"]["recorded_at"] = pd.to_datetime(frames["temps"]["recorded_at"], errors="coerce")
    for col in ["collection_date", "expiry_date", "status_date"]:
        frames["units"][col] = pd.to_datetime(frames["units"][col], errors="coerce")
    frames["transfers"]["dispatched_at"] = pd.to_datetime(frames["transfers"]["dispatched_at"], errors="coerce")
    frames["transfers"]["received_at"] = pd.to_datetime(frames["transfers"]["received_at"], errors="coerce")
    frames["donations"]["collection_date"] = pd.to_datetime(frames["donations"]["collection_date"], errors="coerce")
    frames["donations"]["tested_date"] = pd.to_datetime(frames["donations"]["tested_date"], errors="coerce")
    return frames


def _normalise(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def safe_analytical_views(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Create explicit safe views; source frames and source CSVs remain untouched."""
    facilities = frames["facilities"].set_index("facility_id").name.to_dict()
    requests = frames["requests"].copy()
    requests["facility_name_canonical"] = requests.facility_id.map(facilities)
    requests["patient_blood_group_clean"] = requests.patient_blood_group.where(
        ~requests.patient_blood_group.astype(str).str.lower().eq("unknown"), pd.NA)

    temps = frames["temps"].copy()
    glitch = temps.temp_c.isin([-99.0, 99.9, 0.0])
    temps["temp_c_clean"] = temps.temp_c.mask(glitch)

    transfers = frames["transfers"].copy()
    transfers["receipt_status"] = np.where(transfers.received_at.notna(), "confirmed", "pending_confirmation")

    units = frames["units"].merge(frames["donations"][["donation_id", "screening_result", "tested_date"]],
                                   on="donation_id", how="left")
    exposed = units.temp_excursion_exposed.astype(str).str.lower().isin(["true", "1"])
    asof = frames["stock"].date.max()
    units["eligible_for_planning"] = (units.status.eq("in_stock") & units.screening_result.eq("non_reactive") &
                                      units.tested_date.notna() & ~exposed & units.expiry_date.gt(asof))
    return {"requests": requests, "temps": temps, "transfers": transfers, "units": units}


def dataset_manifest(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """File-level lineage: row/column counts, missing cells, duplicate rows and SHA-256."""
    file_names = {"facilities": "facilities.csv", "units": "units.csv", "requests": "requests.csv",
                  "stock": "daily_stock.csv", "transfers": "transfers.csv", "temps": "temperature_logs.csv",
                  "donors": "donors.csv", "donations": "donations.csv", "outages": "power_outages.csv",
                  "routes": "routes.csv"}
    rows = []
    for key, filename in file_names.items():
        frame = frames[key]
        digest = hashlib.sha256((RAW_DIR / filename).read_bytes()).hexdigest()
        rows.append({"file": filename, "rows": int(len(frame)), "columns": int(len(frame.columns)),
                     "missing_cells": int(frame.isna().sum().sum()), "duplicate_full_rows": int(frame.duplicated().sum()),
                     "sha256": digest})
    return pd.DataFrame(rows)


def data_quality_report(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    donors, requests, transfers, temps, units = (frames[k] for k in ["donors", "requests", "transfers", "temps", "units"])
    identity = ["birth_date", "sex", "home_county", "phone_last4"]
    missing_group = donors.blood_group.isna()
    unknown_group = requests.patient_blood_group.astype(str).str.lower().eq("unknown")
    glitches = temps.temp_c.isin([-99.0, 99.9, 0.0])
    overrange = ((temps.temp_c < 2) | (temps.temp_c > 6)) & ~glitches
    missing_received = transfers.received_at.isna()
    exposed = units.temp_excursion_exposed.astype(str).str.lower().isin(["true", "1"])
    screened_units = units.merge(frames["donations"][["donation_id", "screening_result", "tested_date"]],
                                 on="donation_id", how="left")
    in_stock_unscreened = screened_units.status.eq("in_stock") & (
        ~screened_units.screening_result.eq("non_reactive") | screened_units.tested_date.isna())

    facility_names = frames["facilities"].set_index("facility_id").name.to_dict()
    expected = requests.facility_id.map(facility_names).fillna("")
    unresolved_names = requests.facility_name_raw.fillna("").map(_normalise) != expected.map(_normalise)

    donations = frames["donations"].merge(donors[["donor_id", "sex"]], on="donor_id", how="left")
    donations = donations[donations.outcome.eq("collected")].sort_values(["donor_id", "collection_date"])
    donations["gap_days"] = donations.groupby("donor_id").collection_date.diff().dt.days
    short_gap = ((donations.sex.eq("M") & donations.gap_days.lt(90)) |
                 (donations.sex.eq("F") & donations.gap_days.lt(120)))

    stock = frames["stock"]
    last_date = stock.date.max()
    snapshot_units = int(stock.loc[stock.date.eq(last_date), "units_in_stock_end_of_day"].sum())
    ledger_units = int(units.status.eq("in_stock").sum())
    checks = [
        ("Possible duplicate donor identities", int(donors.duplicated(identity).sum()), "Review", "452 additional donor rows share birth date, sex, county and phone suffix. Flag for human verification; never auto-merge."),
        ("Missing donor blood groups", int(missing_group.sum()), "Warning", "Do not infer a blood group. Keep the donor record incomplete until verified."),
        ("Unknown emergency patient blood groups", int(unknown_group.sum()), "Warning", "Treat unknown as missing and exclude from blood-group-specific matching."),
        ("Unresolved facility labels after ID reconciliation", int(unresolved_names.sum()), "Review", "Join using facility_id and attach the canonical label. Preserve unresolved raw text for review."),
        ("Transfers without receipt confirmation", int(missing_received.sum()), "Review", "Mark receipt as pending confirmation; do not assume delivery or failure."),
        ("Temperature sensor glitches", int(glitches.sum()), "Critical", "Mask -99, 99.9 and 0.0 in the analytical view; preserve raw readings."),
        ("Valid readings outside 2–6°C", int(overrange.sum()), "Critical", "Flag for cold-chain investigation. A reading alone does not determine unit release status."),
        ("Donations inside minimum interval", int(short_gap.sum()), "Warning", "Flag collected donations less than 90 days apart for men or 120 days for women."),
        ("Units marked temperature-exposed", int(exposed.sum()), "Critical", "Exclude from redistribution eligibility and follow blood-service quarantine/release rules."),
        ("In-stock units without a confirmed non-reactive screen", int(in_stock_unscreened.sum()), "Critical", "Exclude from redistribution. Only explicitly non-reactive units with a tested_date are eligible for planning."),
    ]
    record_count = sum(len(frames[k]) for k in ["facilities", "units", "requests", "stock", "transfers", "temps", "donors", "donations", "outages", "routes"])
    return {
        "records_inspected": int(record_count),
        "files_inspected": 10,
        "checks": [{"check": a, "count": b, "severity": c, "handling": d} for a, b, c, d in checks],
        "reconciliation": {"date": last_date.date().isoformat(), "daily_stock_units": snapshot_units,
                           "unit_ledger_units": ledger_units, "difference": snapshot_units - ledger_units},
        "manifest": dataset_manifest(frames),
        "safe_transformations": [
            f"{len(requests):,} requests mapped to canonical facility labels using facility_id; {int(unresolved_names.sum()):,} raw labels retained for review.",
            f"{int(glitches.sum()):,} sensor sentinel values masked in the analytical view; raw readings preserved.",
            f"{int(unknown_group.sum()):,} unknown blood groups treated as missing for group-specific analysis.",
            f"{int(missing_received.sum()):,} transfer receipts marked pending confirmation.",
        ],
    }


def overview_metrics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    units, requests, stock = frames["units"], frames["requests"], frames["stock"]
    last_date = stock.date.max()
    latest = stock[stock.date.eq(last_date)]
    rbc_wb = units[units.component.isin(["RBC", "WB"])]
    wasted = rbc_wb.status.isin(["expired", "discarded_temperature"]).sum()
    weekly = requests.dropna(subset=["requested_at"]).copy()
    weekly["week"] = weekly.requested_at.dt.to_period("W").dt.start_time
    trend = weekly.groupby("week").agg(requested=("units_requested", "sum"), issued=("units_issued", "sum")).reset_index().tail(16)
    facility_names = frames["facilities"].set_index("facility_id").name.to_dict()
    shortage = requests[requests.outcome.ne("fulfilled")].groupby("facility_id").size().sort_values(ascending=False).head(6)
    return {
        "period_start": stock.date.min().date().isoformat(), "period_end": last_date.date().isoformat(),
        "facilities": int(frames["facilities"].facility_id.nunique()), "donors": int(frames["donors"].donor_id.nunique()),
        "units": int(len(units)), "requests": int(len(requests)), "transfers": int(len(frames["transfers"])),
        "stock_total": int(latest.units_in_stock_end_of_day.sum()),
        "fulfilment_pct": round(float(requests.outcome.eq("fulfilled").mean() * 100), 1),
        "requested_units": int(requests.units_requested.sum()), "issued_units": int(requests.units_issued.sum()),
        "waste_pct": round(float(wasted / max(len(rbc_wb), 1) * 100), 1),
        "wasted_rbc_wb": int(wasted), "rbc_wb_total": int(len(rbc_wb)),
        "blood_stock": latest.groupby("blood_group").units_in_stock_end_of_day.sum().reindex(BLOOD_GROUPS, fill_value=0).astype(int).to_dict(),
        "weekly": trend,
        "shortage_sites": [{"facility_id": k, "facility": facility_names.get(k, k), "unfulfilled_requests": int(v)} for k, v in shortage.items()],
    }


def redistribution_opportunities(frames: dict[str, pd.DataFrame], horizon_days: int = 7,
                                 lookback_days: int = 28, max_route_hours: float = 12,
                                 min_shelf_life_days: int = 2, expiry_window_days: int = 14) -> list[dict[str, Any]]:
    facilities, units, requests, stock, transfers, routes = (frames[k] for k in ["facilities", "units", "requests", "stock", "transfers", "routes"])
    asof = stock.date.max()
    start = asof - pd.Timedelta(days=lookback_days)
    facility_rows = facilities.set_index("facility_id").to_dict("index")
    centre_ids = facilities.loc[facilities.facility_type.isin(["regional_blood_centre", "satellite_blood_centre"]), "facility_id"].tolist()
    hospital_rows = facilities.loc[facilities.facility_type.str.contains("hospital|referral", case=False, regex=True)]

    recent_requests = requests[(requests.requested_at > start) & (requests.requested_at <= asof) &
                               (~requests.patient_blood_group.astype(str).str.lower().eq("unknown"))]
    demand = recent_requests.groupby(["facility_id", "component_requested", "patient_blood_group"]).units_requested.sum().to_dict()
    recent_transfers = transfers[(transfers.dispatched_at > start) & (transfers.dispatched_at <= asof)]
    transfer_units = recent_transfers.merge(units[["unit_id", "component", "blood_group"]], on="unit_id", how="left")
    outflow = transfer_units.groupby(["from_facility_id", "component", "blood_group"]).size().to_dict()

    screened_units = units.merge(frames["donations"][["donation_id", "screening_result", "tested_date"]],
                                 on="donation_id", how="left")
    safe = screened_units[(screened_units.status.eq("in_stock")) &
                          (screened_units.screening_result.eq("non_reactive")) &
                          (screened_units.tested_date.notna()) &
                          (~screened_units.temp_excursion_exposed.astype(str).str.lower().isin(["true", "1"]))].copy()
    safe = safe.dropna(subset=["expiry_date"])
    safe = safe[safe.expiry_date > asof]
    grouped_expiry = {key: sorted(group.expiry_date.tolist())
                      for key, group in safe.groupby(["current_facility_id", "component", "blood_group"])}
    safe_stock = safe.groupby(["current_facility_id", "component", "blood_group"]).size().to_dict()
    route_map = {(r.from_facility_id, r.to_facility_id): r for r in routes.itertuples()}
    candidates = []

    for dest in hospital_rows.itertuples():
        dest_id = dest.facility_id
        dest_cold_ok = bool(dest.has_blood_fridge_backup_power) or float(dest.grid_reliability or 0) >= 0.90
        if not dest_cold_ok:
            continue
        for component in ("RBC", "WB"):
            for group in BLOOD_GROUPS:
                expected_demand = demand.get((dest_id, component, group), 0) / lookback_days * horizon_days
                destination_stock = int(safe_stock.get((dest_id, component, group), 0))
                shortfall = max(0, math.ceil(expected_demand - destination_stock))
                if shortfall <= 0:
                    continue
                for source_id in centre_ids:
                    source = facility_rows[source_id]
                    source_cold_ok = bool(source.get("has_blood_fridge_backup_power")) or float(source.get("grid_reliability") or 0) >= 0.90
                    if not source_cold_ok:
                        continue
                    route = route_map.get((source_id, dest_id))
                    if route is None or float(route.typical_travel_hours) > max_route_hours:
                        continue
                    travel_hours = float(route.typical_travel_hours)
                    arrival_buffer = math.ceil(travel_hours / 24) + min_shelf_life_days
                    expiry_dates = grouped_expiry.get((source_id, component, group), [])
                    eligible_dates = [d for d in expiry_dates if d >= asof + pd.Timedelta(days=arrival_buffer)]
                    at_risk = [d for d in eligible_dates if d <= asof + pd.Timedelta(days=expiry_window_days)]
                    reserve = max(1, math.ceil(outflow.get((source_id, component, group), 0) / lookback_days * horizon_days * 1.2))
                    surplus = max(0, len(eligible_dates) - reserve)
                    quantity = min(shortfall, surplus, len(at_risk))
                    if quantity <= 0:
                        continue
                    soonest = at_risk[0]
                    shelf_life_arrival = max(0, (soonest - asof).days - math.ceil(travel_hours / 24))
                    identity = f"{asof.date()}|{source_id}|{dest_id}|{component}|{group}"
                    rid = hashlib.sha256(identity.encode()).hexdigest()[:20]
                    candidates.append({
                        "id": rid, "plan_date": asof.date().isoformat(),
                        "from_id": source_id, "from_name": source["name"],
                        "to_id": dest_id, "to_name": dest.name,
                        "component": component, "blood_group": group, "units": int(quantity),
                        "demand_7d": round(expected_demand, 1), "destination_safe_stock": destination_stock,
                        "shortfall": int(shortfall), "source_eligible": len(eligible_dates),
                        "source_reserve": int(reserve), "source_surplus": int(surplus),
                        "at_risk_units": len(at_risk), "soonest_expiry": soonest.date().isoformat(),
                        "arrival_shelf_life_days": int(shelf_life_arrival),
                        "travel_hours": round(travel_hours, 1), "road_km": round(float(route.road_km), 1),
                        "explanation": (f"{dest.name} has {destination_stock} safe {group} {component} units against "
                                        f"about {expected_demand:.1f} units of {horizon_days}-day demand. {source['name']} "
                                        f"has {len(eligible_dates)} eligible units, retains a {reserve}-unit dispatch "
                                        f"reserve, and has {len(at_risk)} units approaching expiry. The route is "
                                        f"{travel_hours:.1f} typical hours; estimated shelf life on arrival is "
                                        f"at least {shelf_life_arrival} days."),
                    })
    candidates.sort(key=lambda x: (-x["units"], x["soonest_expiry"], x["travel_hours"]))
    return candidates[:30]


def _forecast_fn(train: pd.Series, horizon: int, method: str) -> np.ndarray:
    if method == "7-day mean baseline":
        return np.repeat(float(train.iloc[-7:].mean()), horizon)
    if method == "28-day moving average":
        return np.repeat(float(train.iloc[-28:].mean()), horizon)
    if method == "weekly seasonal naive":
        return np.tile(train.iloc[-7:].to_numpy(dtype=float), int(np.ceil(horizon / 7)))[:horizon]
    raise ValueError(f"Unknown method: {method}")


def forecast_backtest(frames: dict[str, pd.DataFrame], facility_id: str, component: str,
                      blood_group: str, horizon: int = 7, folds: int = 8) -> dict[str, Any]:
    requests = frames["requests"]
    rows = requests[(requests.facility_id == facility_id) &
                    (requests.component_requested == component) &
                    (requests.patient_blood_group == blood_group)]
    if rows.empty:
        return {"error": "No matching request history for this facility, component and blood group."}
    series = rows.groupby(rows.requested_at.dt.floor("D")).units_requested.sum()
    full = pd.date_range(frames["stock"].date.min(), frames["stock"].date.max(), freq="D")
    series = series.reindex(full, fill_value=0.0).astype(float)
    methods = ["7-day mean baseline", "28-day moving average", "weekly seasonal naive"]
    errors = {m: [] for m in methods}
    actuals = []
    for fold in range(folds, 0, -1):
        split = len(series) - fold * horizon
        if split < 56:
            continue
        train = series.iloc[:split]
        actual = series.iloc[split:split + horizon].to_numpy(dtype=float)
        actuals.append(actual)
        for method in methods:
            pred = np.clip(_forecast_fn(train, horizon, method), 0, None)
            errors[method].append(actual - pred)
    if not actuals:
        return {"error": "Insufficient history for rolling-origin evaluation."}
    actual_all = np.concatenate(actuals)
    total_actual = np.abs(actual_all).sum()
    metrics = {}
    residuals = {}
    for method, chunks in errors.items():
        err = np.concatenate(chunks)
        residuals[method] = err
        metrics[method] = {"WAPE": round(float(np.abs(err).sum() / total_actual), 3) if total_actual else None,
                           "MAE": round(float(np.abs(err).mean()), 3)}
    baseline = "7-day mean baseline"
    best = min(methods, key=lambda m: metrics[m]["WAPE"] if metrics[m]["WAPE"] is not None else 99)
    beats_baseline = metrics[best]["WAPE"] is not None and metrics[best]["WAPE"] < metrics[baseline]["WAPE"]
    # If even the best candidate is too inaccurate, fall back to the transparent baseline.
    low_confidence = metrics[best]["WAPE"] is None or metrics[best]["WAPE"] > 0.5
    selected = best if beats_baseline and not low_confidence else baseline
    train = series
    raw_forecast = np.clip(_forecast_fn(train, horizon, selected), 0, None)
    low, high = np.percentile(residuals[selected], [10, 90])
    dates = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
    forecast_rows = [{"date": d.date().isoformat(), "forecast": round(float(v), 2),
                      "low": round(float(max(0, v + low)), 2), "high": round(float(max(0, v + high)), 2)}
                     for d, v in zip(dates, raw_forecast)]
    return {"metrics": metrics, "best_candidate": best, "selected_model": selected, "baseline": baseline,
            "baseline_wape": metrics[baseline]["WAPE"], "best_candidate_wape": metrics[best]["WAPE"],
            "selected_wape": metrics[selected]["WAPE"], "beats_baseline": bool(beats_baseline),
            "low_confidence": bool(low_confidence), "fallback_used": bool(low_confidence),
            "forecast": forecast_rows, "series": series.reset_index().rename(columns={"index": "date", 0: "actual"})}


def init_audit(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else LOCAL_DIR / "decisions.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS decisions (
            recommendation_id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL, to_id TEXT NOT NULL,
            component TEXT NOT NULL, blood_group TEXT NOT NULL,
            proposed_units INTEGER NOT NULL, decided_units INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('accept','change','reject')),
            reason TEXT, reviewer TEXT NOT NULL, decided_at TEXT NOT NULL
        )""")
    return path


def record_decision(proposal: dict[str, Any], decision: str, reviewer: str,
                    reason: str = "", units: int | None = None, db_path: str | Path | None = None) -> None:
    if decision not in {"accept", "change", "reject"}:
        raise ValueError("Decision must be accept, change or reject.")
    if decision in {"change", "reject"} and not reason.strip():
        raise ValueError("A reason is required when changing or rejecting a recommendation.")
    decided_units = proposal["units"] if decision == "accept" else (0 if decision == "reject" else units)
    if decision == "change" and (decided_units is None or not 1 <= int(decided_units) <= proposal["units"]):
        raise ValueError(f"Changed quantity must be between 1 and {proposal['units']}.")
    path = init_audit(db_path)
    try:
        with sqlite3.connect(path) as con:
            con.execute("""INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                        (proposal["id"], proposal["from_id"], proposal["to_id"], proposal["component"],
                         proposal["blood_group"], proposal["units"], int(decided_units), decision,
                         reason.strip() or None, reviewer.strip() or "Demo reviewer"))
    except sqlite3.IntegrityError as exc:
        raise ValueError("A decision has already been recorded for this recommendation.") from exc


def load_decisions(db_path: str | Path | None = None) -> pd.DataFrame:
    path = init_audit(db_path)
    with sqlite3.connect(path) as con:
        return pd.read_sql_query("SELECT * FROM decisions ORDER BY decided_at DESC", con)


def sms_draft(proposal: dict[str, Any], limit: int = 160) -> str:
    text = (f"ABBIS: Review {proposal['units']} {proposal['blood_group']} {proposal['component']} units: "
            f"{proposal['from_id']} to {proposal['to_id']}. Route {proposal['travel_hours']}h. "
            f"Expiry {proposal['soonest_expiry']}. Coordinator approval required.")
    return text[:limit]
