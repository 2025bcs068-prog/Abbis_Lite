# ABBIS Lite — 2:50 demo video script

**Maximum allowed:** 3 minutes. Aim for 2:45–2:55. Record at 1080p, 16:9. Close notifications and avoid showing personal data.

| Time | Screen/action | Voice-over |
|---|---|---|
| 0:00–0:15 | ABBIS Lite title, then Overview | “A blood unit can approach expiry at one facility while another hospital struggles to meet demand. ABBIS Lite is a blood-network decision-support prototype that helps teams spot those opportunities earlier, while keeping a person in control.” |
| 0:15–0:38 | Overview: point to four KPIs, weekly demand/issue trend, blood-group stock and snapshot reconciliation | “The overview gives a compact network picture: 47 facilities, 49,426 unit records and 17,430 requests. It compares weekly demand with units issued and shows the final stock snapshot. The daily-stock total and unit ledger reconcile to 8,666 units, with zero difference.” |
| 0:38–1:03 | Data quality: show the issue table and safe transformations | “We start with data integrity. ABBIS flags possible duplicate donor identities, missing and unknown blood groups, unconfirmed transfers and temperature sensor glitches. We preserve the raw data, use facility IDs as the join key and never guess clinical facts.” |
| 1:03–1:48 | Redistribution planner: show the first Kisumu-to-Siaya recommendation, explain quantity, stock, reserve, expiry, route and shelf life; record Accept or Change with a reason | “The matcher estimates seven-day demand from the previous 28 days. It looks for exact group and component matches, excludes temperature-exposed units, retains a source reserve, checks the route and destination cold-chain readiness, and prioritises units approaching expiry. Here it identifies two AB-positive red-cell units from Kisumu for Siaya. A reviewer can Accept, Change or Reject, with a reason where required. The local log records the decision; it does not dispatch blood.” |
| 1:48–2:25 | Demand forecast: HSP-018, A+, RBC; show comparison and fallback | “Forecasts are tested with rolling historical windows against a simple seven-day mean baseline. In this example the 28-day average improves WAPE from 1.016 to 0.953, but the error is still too high. ABBIS therefore falls back to the baseline and makes the uncertainty visible instead of claiming an unreliable prediction.” |
| 2:25–2:42 | Decision audit and SMS draft | “Every review decision is recorded locally, and a short SMS draft supports low-connectivity workflows. Sending and cross-device synchronization are not yet implemented.” |
| 2:42–2:55 | About ABBIS | “The starter dataset is synthetic and Kenya-modelled. ABBIS Lite is a hackathon prototype, not a certified clinical system. Better visibility, earlier action, safer decisions.” |

## Before recording

- [ ] Run `./run.sh` and open the Streamlit app.
- [ ] Show actual dashboard interactions; do not use a static slide as the whole demo.
- [ ] Use the first Kisumu → Siaya recommendation if it is still pending.
- [ ] If it has already been decided, use another pending recommendation or reset only the local demo audit database before recording.
- [ ] Show the high forecast error and fallback honestly.
- [ ] Do not claim physical dispatch, blood saved or clinical safety certification.
- [ ] Confirm the final video is under 3:00 and viewable by anyone with the link.
