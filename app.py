from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from abbis.engine import (
    BLOOD_GROUPS, COMPONENTS, RAW_DIR, data_quality_report, forecast_backtest,
    load_decisions, load_frames, overview_metrics, redistribution_opportunities,
    record_decision, sms_draft,
)

st.set_page_config(page_title="ABBIS Lite | Blood Network Intelligence", page_icon="🩸",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--navy:#10213b;--navy2:#172c4b;--teal:#0a8990;--teal2:#42c2bd;--ink:#1b2b45;--muted:#718198;--line:#e5ebf2;--bg:#f4f7fb;--red:#c84c58;--green:#16815c;--amber:#a96a18}
html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink)}
.stApp{background:var(--bg)}
[data-testid="stHeader"]{background:rgba(244,247,251,.92)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#10213b 0%,#172d4c 100%);border-right:1px solid #243c5d}
[data-testid="stSidebar"] *{color:#d9e4f2}
[data-testid="stSidebar"] .stRadio label{font-size:13px;font-weight:600;padding:5px 0}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#aebdd0}
[data-testid="stSidebar"] hr{border-color:#334a68}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3{font-family:Inter,system-ui,sans-serif,sans-serif;letter-spacing:-.035em;color:var(--ink)}
h1{font-size:2rem!important;font-weight:800!important;margin-bottom:.15rem!important}
h2{font-size:1.25rem!important;font-weight:800!important}
h3{font-size:1rem!important;font-weight:750!important}
p{color:#5f6f85}
.abbis-brand{display:flex;align-items:center;gap:10px;margin:4px 0 22px}
.abbis-drop{width:35px;height:43px;background:linear-gradient(145deg,#5be0d4,#07939a);border-radius:60% 40% 60% 40%/65% 55% 45% 35%;transform:rotate(45deg);box-shadow:0 5px 18px #0a8b8b55}
.abbis-word{font-family:Inter,system-ui,sans-serif;font-weight:800;letter-spacing:.13em;font-size:18px;color:white}
.abbis-sub{font-size:9px;letter-spacing:.17em;color:#91a8c2;margin-top:2px}
.page-kicker{font-size:10px;letter-spacing:.18em;font-weight:800;color:var(--teal);margin-bottom:5px}
.page-subtitle{font-size:12px;color:#7b899d;margin-top:4px;margin-bottom:20px}
.metric-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:17px 18px;box-shadow:0 7px 22px #17335308;min-height:116px}
.metric-label{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#8290a3;font-weight:750}
.metric-value{font-family:Inter,system-ui,sans-serif;font-size:30px;line-height:1.2;font-weight:800;color:#1b2e4b;margin:8px 0 3px}
.metric-note{font-size:10px;color:#8b98a9}
.metric-accent .metric-value{color:var(--teal)}
.metric-danger .metric-value{color:var(--red)}
.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:0 7px 22px #17335308;margin-bottom:14px}
.panel-title{font-size:13px;font-weight:800;color:#233652;margin-bottom:3px}
.panel-sub{font-size:10px;color:#8794a6;margin-bottom:12px}
.alert-banner{display:flex;gap:12px;align-items:center;background:#fff7eb;border:1px solid #f0dfc1;border-radius:12px;padding:12px 15px;margin:16px 0}
.alert-dot{width:25px;height:25px;border-radius:50%;background:#f1dfbd;color:#98651b;display:grid;place-items:center;font-weight:900;flex:none}
.alert-text strong{font-size:11px;color:#78521a}.alert-text span{font-size:10px;color:#9b7a4c;display:block}
.route-pill{font-size:9px;font-weight:800;color:#0b7780;background:#e6f5f5;padding:5px 8px;border-radius:6px;display:inline-block}
.status-pill{font-size:8px;font-weight:850;letter-spacing:.08em;border-radius:5px;padding:5px 8px;background:#fff4e6;color:#9a681f}
.status-pill.accept{background:#eaf7f0;color:#16815c}.status-pill.change{background:#edf2ff;color:#4b6695}.status-pill.reject{background:#fff0f0;color:#c84c58}
.small-muted{font-size:10px;color:#8391a3}
.stButton>button{border-radius:8px;font-weight:750;font-size:11px;padding:.52rem .9rem;border:1px solid #0a8990;background:#0a8990;color:#fff}
.stButton>button:hover{border-color:#08777e;background:#08777e;color:#fff}
.stDownloadButton>button{border-radius:8px}
div[data-testid="stForm"]{border:1px solid #e8edf3;border-radius:10px;padding:10px;background:#fbfcfe}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:9px}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
[data-testid="stMetricLabel"]{font-size:10px}
[data-testid="stMetricValue"]{font-family:Inter,system-ui,sans-serif;font-weight:800}
hr{border-color:var(--line)}
footer{visibility:hidden}
@media(max-width:800px){.block-container{padding-left:1rem;padding-right:1rem}.metric-value{font-size:24px}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Reading the synthetic blood-system dataset…")
def get_frames():
    return load_frames(RAW_DIR)


frames = get_frames()
metrics = overview_metrics(frames)
quality = data_quality_report(frames)

with st.sidebar:
    st.markdown("""
    <div class="abbis-brand"><div class="abbis-drop"></div><div>
      <div class="abbis-word">ABBIS LITE</div>
      <div class="abbis-sub">BLOOD NETWORK INTELLIGENCE</div>
    </div></div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='font-size:9px;letter-spacing:.16em;font-weight:800;color:#8199b5;margin:8px 0'>WORKSPACE</div>", unsafe_allow_html=True)
    page = st.radio("Navigation", ["Overview", "Data quality", "Redistribution planner", "Demand forecast", "Decision audit", "About ABBIS"],
                    label_visibility="collapsed")
    st.divider()
    reviewer = st.text_input("Reviewer identity", value=st.session_state.get("reviewer", "Coordinator Demo"),
                             help="Local demo label only; this prototype does not authenticate reviewer identities.")
    st.session_state["reviewer"] = reviewer.strip() or "Demo reviewer"
    st.markdown("<div style='font-size:9px;color:#8da2bc;margin-top:10px'>SYNTHETIC DATA · READ-ONLY SOURCE FILES</div>", unsafe_allow_html=True)


def page_header(kicker: str, title: str, subtitle: str):
    st.markdown(f"<div class='page-kicker'>{kicker}</div><h1>{title}</h1><div class='page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str, note: str = "", tone: str = ""):
    st.markdown(f"<div class='metric-card {tone}'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)


def panel_title(title: str, subtitle: str = ""):
    st.markdown(f"<div class='panel-title'>{title}</div><div class='panel-sub'>{subtitle}</div>", unsafe_allow_html=True)


def get_decisions():
    return load_decisions()


if page == "Overview":
    page_header("NETWORK COMMAND CENTRE", "Blood network overview", f"Evidence from {metrics['period_start']} to {metrics['period_end']} · Official synthetic starter dataset")
    cols = st.columns(4, gap="medium")
    cards = [
        ("Facilities monitored", f"{metrics['facilities']:,}", "47-site network"),
        ("Blood units tracked", f"{metrics['units']:,}", "Unit-level lifecycle records"),
        ("Hospital requests", f"{metrics['requests']:,}", f"{metrics['requested_units']:,} units requested"),
        ("Request fulfilment", f"{metrics['fulfilment_pct']:.1f}%", f"{metrics['issued_units']:,} units issued"),
    ]
    for col, (label, value, note) in zip(cols, cards):
        with col:
            metric_card(label, value, note, "metric-accent" if label == "Request fulfilment" else "")

    st.markdown(f"""
    <div class="alert-banner"><div class="alert-dot">!</div><div class="alert-text">
      <strong>{metrics['wasted_rbc_wb']:,} RBC / whole-blood units recorded as wasted ({metrics['waste_pct']:.1f}%)</strong>
      <span>Expired or discarded after temperature exposure · review cold-chain and redistribution risks</span>
    </div><span class="route-pill">STOCK SNAPSHOT: {metrics['stock_total']:,}</span></div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        with st.container(border=True):
            panel_title("Demand vs fulfilment", "Weekly units requested compared with units issued")
            trend = metrics["weekly"].melt(id_vars="week", value_vars=["requested", "issued"], var_name="series", value_name="units")
            fig = px.line(trend, x="week", y="units", color="series", markers=True,
                          color_discrete_map={"requested": "#0a8990", "issued": "#aab7c7"})
            fig.update_layout(height=290, margin=dict(l=5, r=5, t=10, b=5), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", legend_title=None, font=dict(family="Inter", size=10, color="#718198"),
                              xaxis_title=None, yaxis_title="Units", hovermode="x unified")
            fig.update_xaxes(showgrid=False, tickformat="%d %b")
            fig.update_yaxes(gridcolor="#edf1f5", zeroline=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            panel_title("Available stock by blood group", f"Latest end-of-day snapshot · {metrics['period_end']}")
            stock_df = pd.DataFrame({"Blood group": list(metrics["blood_stock"].keys()), "Units": list(metrics["blood_stock"].values())})
            fig = px.bar(stock_df, x="Blood group", y="Units", color="Blood group",
                         color_discrete_sequence=["#0a8990", "#3ba8ad", "#79c9c7", "#a7dcd8"])
            fig.update_layout(height=290, showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family="Inter", size=10, color="#718198"), xaxis_title=None, yaxis_title="Units")
            fig.update_yaxes(gridcolor="#edf1f5")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        with st.container(border=True):
            panel_title("Facilities needing attention", "Highest number of requests not fully fulfilled")
            st.dataframe(pd.DataFrame(metrics["shortage_sites"]), hide_index=True, use_container_width=True,
                         column_config={"facility_id": "Facility ID", "facility": "Facility", "unfulfilled_requests": st.column_config.NumberColumn("Unfulfilled", format="%d")})
    with right:
        with st.container(border=True):
            panel_title("Snapshot integrity", "Independent stock reconciliation")
            rec = quality["reconciliation"]
            a, b, c = st.columns(3)
            a.metric("Daily stock", f"{rec['daily_stock_units']:,}")
            b.metric("Unit ledger", f"{rec['unit_ledger_units']:,}")
            c.metric("Difference", f"{rec['difference']:,}", delta="Reconciled" if rec["difference"] == 0 else "Review", delta_color="normal" if rec["difference"] == 0 else "inverse")
            st.caption("Aggregate snapshot and unit ledger agree at the final data date. This does not itself certify each unit for release.")
    st.caption("All figures are from synthetic, Kenya-modelled hackathon data. They are not real hospital performance statistics.")


elif page == "Data quality":
    page_header("TRUST BEFORE INTELLIGENCE", "Data quality observatory", "Find defects, preserve evidence and make safe analytical transformations explicit.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Records inspected", f"{quality['records_inspected']:,}")
    c2.metric("Quality checks", len(quality["checks"]))
    c3.metric("Stock reconciliation difference", f"{quality['reconciliation']['difference']:,}")
    st.markdown("### Detected data issues")
    qdf = pd.DataFrame(quality["checks"])
    st.dataframe(qdf, hide_index=True, use_container_width=True,
                 column_config={"check": "Validation check", "count": st.column_config.NumberColumn("Records", format="%d"), "severity": "Severity", "handling": "ABBIS handling"})
    st.markdown("### Safe analytical transformations")
    for item in quality["safe_transformations"]:
        st.markdown(f"- {item}")
    with st.expander("Stock snapshot reconciliation"):
        rec = quality["reconciliation"]
        st.write(f"At **{rec['date']}**, daily_stock.csv reports **{rec['daily_stock_units']:,}** units. The unit ledger reports **{rec['unit_ledger_units']:,}** rows with status `in_stock`. Difference: **{rec['difference']:,}**.")
    with st.expander("Source file manifest and SHA-256 fingerprints"):
        st.dataframe(quality["manifest"], hide_index=True, use_container_width=True,
                     column_config={"file": "Source file", "rows": st.column_config.NumberColumn("Rows", format="%d"),
                                    "columns": st.column_config.NumberColumn("Columns", format="%d"),
                                    "missing_cells": st.column_config.NumberColumn("Missing cells", format="%d"),
                                    "duplicate_full_rows": st.column_config.NumberColumn("Duplicate rows", format="%d"),
                                    "sha256": st.column_config.TextColumn("SHA-256")})
    st.info("Raw CSV files are immutable. Suspected donor duplicates, missing blood groups and temperature anomalies are flagged for review; ABBIS never guesses clinical facts.")


elif page == "Redistribution planner":
    plan_date = frames["stock"].date.max().date().isoformat()
    page_header("EXPLAINABLE REDISTRIBUTION", "Network opportunities", f"A conservative 7-day planner using the official starter dataset · planning date {plan_date}")
    proposals = redistribution_opportunities(frames)
    decisions = get_decisions()
    decided_ids = set(decisions.recommendation_id.tolist()) if not decisions.empty else set()
    f1, f2 = st.columns([1, 1])
    with f1:
        component_filter = st.selectbox("Component", ["All components", "RBC", "WB"], index=0)
    with f2:
        group_filter = st.selectbox("Blood group", ["All groups"] + BLOOD_GROUPS, index=0)
    shown = [p for p in proposals if (component_filter == "All components" or p["component"] == component_filter)
             and (group_filter == "All groups" or p["blood_group"] == group_filter)]
    m1, m2, m3 = st.columns(3)
    m1.metric("Candidate moves", len(shown))
    m2.metric("Potential units at expiry risk", sum(p["units"] for p in shown))
    m3.metric("Human decisions recorded", len(decided_ids))
    st.markdown("""<div class="panel"><div class="panel-title">How the matcher works</div>
    <div class="panel-sub">28-day observed request rate → 7-day demand estimate → safe stock → source reserve → expiry and route filters</div>
    <span class="route-pill">EXACT GROUP + COMPONENT</span> &nbsp; <span class="route-pill">COLD-CHAIN SCREENED</span> &nbsp; <span class="route-pill">HUMAN APPROVAL</span></div>""", unsafe_allow_html=True)

    if not shown:
        st.info("No safe opportunities match these filters. ABBIS does not force a transfer when constraints are not met.")
    for p in shown:
        with st.container(border=True):
            head1, head2 = st.columns([3, 1])
            with head1:
                st.markdown(f"**{p['units']} × {p['blood_group']} {p['component']}**")
                st.caption(f"{p['from_name']}  →  {p['to_name']}")
            with head2:
                if p["id"] in decided_ids:
                    row = decisions[decisions.recommendation_id.eq(p["id"])].iloc[0]
                    st.markdown(f"<span class='status-pill {row['decision']}'>{row['decision'].upper()}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='status-pill'>PENDING REVIEW</span>", unsafe_allow_html=True)
            st.write(p["explanation"])
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("7-day demand", f"{p['demand_7d']:.1f}")
            d2.metric("Safe destination stock", p["destination_safe_stock"])
            d3.metric("Source reserve", p["source_reserve"])
            d4.metric("Road distance", f"{p['road_km']:.1f} km")
            d5.metric("Shelf life on arrival", f"{p['arrival_shelf_life_days']} days")
            if p["id"] in decided_ids:
                st.caption(f"Recorded by {row['reviewer']} · {row['decided_at']} · {row['reason'] or 'No additional reason'}")
            else:
                with st.form(f"decision_{p['id']}"):
                    qty_col, reason_col = st.columns([1, 3])
                    with qty_col:
                        changed_units = st.number_input("Units if changed", min_value=1, max_value=int(p["units"]), value=int(p["units"]), key=f"qty_{p['id']}")
                    with reason_col:
                        reason = st.text_input("Reason (required for Change / Reject)", key=f"reason_{p['id']}", max_chars=500)
                    b1, b2, b3 = st.columns(3)
                    accept = b1.form_submit_button("Accept", type="primary", use_container_width=True)
                    change = b2.form_submit_button("Change quantity", use_container_width=True)
                    reject = b3.form_submit_button("Reject", use_container_width=True)
                    if accept or change or reject:
                        action = "accept" if accept else ("change" if change else "reject")
                        try:
                            record_decision(p, action, st.session_state["reviewer"], reason, int(changed_units))
                            st.success(f"{action.title()} decision recorded. No stock has been dispatched.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
            with st.expander("Draft a low-connectivity SMS"):
                st.text_area("SMS draft · maximum 160 characters", value=sms_draft(p), height=75, key=f"sms_{p['id']}")
    st.warning("These are planning recommendations, not dispatch instructions. Decisions are stored in a local SQLite audit log; this prototype does not move physical stock or synchronize decisions across devices.")


elif page == "Demand forecast":
    page_header("DEMAND INTELLIGENCE", "Forecast and baseline evaluation", "Rolling-origin backtesting · no future information used in historical evaluation")
    facilities = frames["facilities"].copy()
    facilities = facilities[facilities.facility_type.str.contains("hospital|referral", case=False, regex=True)]
    facility_map = dict(zip(facilities.facility_id, facilities.name))
    ids = list(facility_map.keys())
    default_idx = ids.index("HSP-018") if "HSP-018" in ids else 0
    a, b, c = st.columns(3)
    with a:
        facility_id = st.selectbox("Facility", ids, index=default_idx, format_func=lambda x: f"{x} · {facility_map[x]}")
    with b:
        component = st.selectbox("Component", ["RBC", "WB", "PLT", "FFP"], index=0)
    with c:
        blood_group = st.selectbox("Blood group", BLOOD_GROUPS, index=0)
    result = forecast_backtest(frames, facility_id, component, blood_group)
    if "error" in result:
        st.warning(result["error"])
    else:
        if result["fallback_used"]:
            st.warning(f"Low-confidence series: the best candidate ({result['best_candidate']}, WAPE {result['best_candidate_wape']:.3f}) still exceeds the 0.50 error gate. ABBIS falls back to the transparent 7-day mean baseline.")
        else:
            st.success(f"Selected {result['selected_model']} because it beat the 7-day baseline on rolling-origin WAPE.")
        k1, k2, k3 = st.columns(3)
        k1.metric("Baseline WAPE", f"{result['baseline_wape']:.3f}")
        k2.metric("Best candidate WAPE", f"{result['best_candidate_wape']:.3f}")
        k3.metric("Selected method", result["selected_model"])
        with st.container(border=True):
            panel_title("Rolling-origin model comparison", "8 historical folds · 7-day horizon · WAPE and MAE; lower is better")
            comparison = pd.DataFrame.from_dict(result["metrics"], orient="index").reset_index().rename(columns={"index": "Method"})
            st.dataframe(comparison, hide_index=True, use_container_width=True)
        with st.container(border=True):
            panel_title("Next 7 days", "Selected forecast with an 80% residual interval")
            hist = result["series"].tail(60)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.date, y=hist.units_requested, mode="lines", name="Observed demand", line=dict(color="#9aa9bc", width=2)))
            fc = pd.DataFrame(result["forecast"])
            fig.add_trace(go.Scatter(x=fc.date, y=fc.high, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=fc.date, y=fc.low, mode="lines", fill="tonexty", fillcolor="rgba(10,137,144,.14)", line=dict(width=0), name="80% interval"))
            fig.add_trace(go.Scatter(x=fc.date, y=fc.forecast, mode="lines+markers", name="Selected forecast", line=dict(color="#0a8990", width=3)))
            fig.update_layout(height=330, margin=dict(l=5,r=5,t=10,b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family="Inter", size=10, color="#718198"), legend_title=None, xaxis_title=None, yaxis_title="Units")
            fig.update_yaxes(gridcolor="#edf1f5")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Forecasts are estimates. Sparse demand can produce high WAPE; ABBIS displays the error and uses the baseline fallback rather than hiding uncertainty.")


elif page == "Decision audit":
    page_header("HUMAN OVERSIGHT", "Decision audit trail", "Local record of who reviewed each redistribution opportunity, what they decided and why.")
    audit = get_decisions()
    if audit.empty:
        st.info("No decisions recorded yet. Open Redistribution planner and review a proposal.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Decisions recorded", len(audit))
        c2.metric("Accepted / changed", int(audit.decision.isin(["accept", "change"]).sum()))
        c3.metric("Rejected", int(audit.decision.eq("reject").sum()))
        st.dataframe(audit, hide_index=True, use_container_width=True)
        st.download_button("Download audit CSV", audit.to_csv(index=False).encode("utf-8"),
                           file_name="abbis_decision_audit.csv", mime="text/csv")
    st.warning("This is a local demo audit log, not a tamper-proof or authenticated production audit service. Decisions are not synchronized across devices.")


elif page == "About ABBIS":
    page_header("PRODUCT BRIEF", "About ABBIS Lite", "Better visibility. Earlier action. Safer decisions.")
    st.markdown("""
    <div class="panel" style="background:linear-gradient(120deg,#10213b,#1a405d);color:white">
      <div style="font-size:10px;letter-spacing:.18em;color:#62d1ca;font-weight:800">BLOOD NETWORK INTELLIGENCE</div>
      <div style="font-family:Manrope;font-size:23px;font-weight:800;color:white;margin:8px 0">A smarter redistribution workflow for blood services.</div>
      <div style="font-size:12px;color:#d0dcea;max-width:900px">ABBIS Lite helps blood-service coordinators identify facilities at risk of shortage while suitable stock may be approaching expiry elsewhere. It explains each recommendation and keeps a person in control.</div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("### The problem")
            st.write("Stock, requests, expiry, transfers and cold-chain records are often fragmented. A facility may hold units nearing expiry while another cannot fully meet demand.")
        with st.container(border=True):
            st.markdown("### What makes ABBIS different")
            st.markdown("- Data quality checks before recommendations\n- Exact blood-group and component matching\n- Expiry-aware stock and route feasibility\n- Source reserve and destination cold-chain checks\n- Forecast comparison against a simple baseline\n- Human Accept / Change / Reject with a reason")
    with col2:
        with st.container(border=True):
            st.markdown("### Safety boundaries")
            st.markdown("- Never infer an unknown blood group\n- Never include temperature-exposed units in a proposal\n- Never override laboratory screening or clinical compatibility\n- Never dispatch automatically\n- Show forecast error and fallback status")
        with st.container(border=True):
            st.markdown("### Technology")
            st.markdown("**Python · Streamlit · Pandas · Plotly · SQLite**\n\nThe raw starter dataset remains read-only. Safe analytical views and the local decision log are stored separately.")
    st.markdown("### Data and limitations")
    st.write("The supplied one-year dataset is synthetic and modelled on Kenya. It does not describe real facilities or real patient outcomes. This is a hackathon prototype, not a certified blood-bank information system. A real pilot would require blood-service governance, local clinical rules, secure authenticated roles, validated cold-chain controls and cross-device synchronization.")
    st.caption("ABBIS Lite · Terumo BCT Africa Hackathon 2026 · Challenge area: Redistribution")

