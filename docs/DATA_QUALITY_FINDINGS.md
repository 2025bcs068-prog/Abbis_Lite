# ABBIS Lite — measured starter dataset findings

**Source:** Terumo BCT Africa Hackathon 2026 synthetic starter dataset  
**Period:** 1 November 2025–31 October 2026  
**Scope:** 10 CSV tables; 782,646 records inspected.  
**Important:** This dataset is synthetic and Kenya-modelled. It is not real facility performance data.

## Quality checks

| Finding | Observed count | Safe handling |
|---|---:|---|
| Additional donor rows sharing a composite identity (birth date, sex, county, phone suffix) | 452 | Flag for human verification; never auto-merge |
| Donor records without blood group | 506 | Keep unknown; never infer |
| Requests with patient blood group `unknown` | 442 | Exclude from group-specific matching |
| Facility labels unresolved after ID-based normalization | 710 | Join by `facility_id`; preserve raw label for review |
| Transfers without `received_at` | 1,046 | Mark pending confirmation |
| Temperature sentinel values (-99, 99.9, 0.0) | 55 | Mask in analytical view; preserve raw values |
| Valid temperature readings outside 2–6°C | 4,607 | Flag for cold-chain investigation |
| Collected donations inside minimum interval (90 days men / 120 days women) | 67 | Flag for eligibility review |
| Units marked temperature-exposed | 7,112 | Exclude from redistribution eligibility |
| In-stock units without a confirmed non-reactive screen | 0 | Only explicitly non-reactive, tested units are eligible |

The dataset notes describe approximately 60 sensor glitches. The supplied `temperature_logs.csv` contains **55** values matching the stated sentinel values. ABBIS reports the observed file count.

## Stock snapshot reconciliation

At 31 October 2026:

| Source | Units |
|---|---:|
| `daily_stock.csv` end-of-day total | 8,666 |
| `units.csv` rows with `status = in_stock` | 8,666 |
| Difference | **0** |

This is an aggregate reconciliation only. It does not mean every in-stock unit is clinically releasable. Temperature-exposed units are filtered separately.

## Operational picture

- 47 facilities, 43,363 donor records, 49,426 unit records, 17,430 hospital requests and 35,181 transfer records.
- 15,189 of 17,430 requests were fully fulfilled: **87.1% request-level fulfilment**.
- 34,242 units were requested and 29,650 issued.
- 8,620 of 37,147 RBC and whole-blood records were expired or discarded after temperature exposure: **23.2%**.

## Example redistribution opportunity

The conservative seven-day matcher identifies **18 candidate opportunities** in the final snapshot. One example:

- **Source:** Kisumu Regional Blood Transfusion Centre (`RBTC-KSM`)
- **Destination:** Siaya County Referral Hospital (`HSP-014`)
- **Product:** 2 × AB+ RBC
- **Destination:** 1 safe unit on hand against approximately 3.2 units of seven-day demand; projected shortfall 3
- **Source:** 19 eligible units, with a 3-unit reserve retained; 2 units are approaching expiry
- **Route:** 73.9 km and 1.7 typical hours
- **Estimated shelf life on arrival:** at least 13 days

This is a planning suggestion, not a dispatch instruction or a claim that units were saved. A human reviewer must decide. The local audit log records the decision but does not move physical stock.

## Method and guardrails

1. Preserve raw CSVs; safe analytical views are written separately.
2. Use `facility_id` as the canonical join key.
3. Treat unknown blood groups as missing, not compatible.
4. Mask known sensor sentinel values; do not treat them as real temperatures.
5. Treat missing receipt times as pending confirmation.
6. Match exact blood-group and component pairs only.
7. Require an explicit non-reactive screen and tested date.
8. Exclude temperature-exposed units.
9. Require source/destination cold-chain readiness, a route no longer than 12 typical hours and at least two days of shelf life on arrival.
10. Estimate seven-day demand from the preceding 28 days and retain a source reserve based on recent transfer outflow.
11. Require Accept/Change/Reject human review; never auto-dispatch.
