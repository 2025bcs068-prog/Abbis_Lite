from pathlib import Path
import tempfile

from abbis.engine import (data_quality_report, forecast_backtest, load_frames,
                          load_decisions, overview_metrics, record_decision,
                          redistribution_opportunities)


def frames():
    return load_frames()


def test_starter_dataset_profile_and_snapshot_reconciliation():
    f = frames()
    report = data_quality_report(f)
    checks = {x["check"]: x["count"] for x in report["checks"]}
    assert len(f["facilities"]) == 47
    assert len(f["units"]) == 49426
    assert len(f["requests"]) == 17430
    assert checks["Possible duplicate donor identities"] == 452
    assert checks["Missing donor blood groups"] == 506
    assert checks["Temperature sensor glitches"] == 55
    assert report["reconciliation"]["difference"] == 0


def test_redistribution_matcher_uses_safe_exact_matches_and_real_routes():
    f = frames()
    proposals = redistribution_opportunities(f)
    assert len(proposals) == 18
    p = proposals[0]
    assert p["component"] in {"RBC", "WB"}
    assert p["blood_group"] in {"O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"}
    assert p["units"] <= p["shortfall"]
    assert p["travel_hours"] <= 12
    assert p["arrival_shelf_life_days"] >= 2


def test_forecast_compares_models_to_seven_day_baseline():
    result = forecast_backtest(frames(), "HSP-018", "RBC", "A+")
    assert "error" not in result
    assert result["baseline"] == "7-day mean baseline"
    assert "28-day moving average" in result["metrics"]
    assert len(result["forecast"]) == 7


def test_audit_records_one_decision_per_recommendation():
    proposal = redistribution_opportunities(frames())[0]
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "audit.sqlite"
        record_decision(proposal, "change", "Coordinator Demo", "Need only one unit", 1, db)
        rows = load_decisions(db)
        assert len(rows) == 1
        assert rows.iloc[0]["decision"] == "change"
        try:
            record_decision(proposal, "accept", "Coordinator Demo", db_path=db)
        except ValueError as exc:
            assert "already" in str(exc)
        else:
            raise AssertionError("Duplicate decisions must be rejected")


def test_low_confidence_forecast_falls_back_to_simple_baseline():
    result = forecast_backtest(frames(), "HSP-018", "RBC", "A+")
    assert result["low_confidence"] is True
    assert result["fallback_used"] is True
    assert result["selected_model"] == "7-day mean baseline"
    assert result["best_candidate"] == "28-day moving average"
    assert result["best_candidate_wape"] < result["baseline_wape"]


def test_source_manifest_has_sha256_and_duplicate_counts():
    from abbis.engine import dataset_manifest
    manifest = dataset_manifest(frames())
    assert len(manifest) == 10
    assert manifest.sha256.str.len().eq(64).all()
    assert manifest.rows.sum() == 782646


def test_safe_views_flag_without_mutating_raw_source():
    from abbis.engine import safe_analytical_views
    f = frames()
    views = safe_analytical_views(f)
    assert views["temps"].temp_c_clean.isna().sum() == 55
    assert views["requests"].patient_blood_group_clean.isna().sum() == 442
    assert views["transfers"].receipt_status.eq("pending_confirmation").sum() == 1046
    assert f["temps"].temp_c.isin([-99.0, 99.9, 0.0]).sum() == 55


def test_redistribution_requires_nonreactive_screen_and_test_date():
    from abbis.engine import safe_analytical_views
    f = frames()
    views = safe_analytical_views(f)
    eligible = views["units"].eligible_for_planning
    assert int(eligible.sum()) == 8555
    assert int((views["units"].status.eq("in_stock") & ~eligible).sum()) == 111
    report = data_quality_report(f)
    screening = next(x for x in report["checks"] if x["check"].startswith("In-stock units without"))
    assert screening["count"] == 0
