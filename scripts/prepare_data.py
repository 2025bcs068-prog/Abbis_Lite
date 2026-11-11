"""Profile source CSVs and write explicit, reversible analytical views."""
import json
from pathlib import Path

from abbis.engine import RAW_DIR, data_quality_report, dataset_manifest, load_frames, safe_analytical_views

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    frames = load_frames(RAW_DIR)
    report = data_quality_report(frames)
    (PROCESSED / "data_quality_report.json").write_text(json.dumps({k: v for k, v in report.items() if k != "manifest"}, indent=2), encoding="utf-8")
    dataset_manifest(frames).to_csv(PROCESSED / "data_manifest.csv", index=False)
    views = safe_analytical_views(frames)
    views["requests"].to_csv(PROCESSED / "requests_clean.csv", index=False)
    views["temps"].to_csv(PROCESSED / "temperature_logs_clean.csv", index=False)
    views["transfers"].to_csv(PROCESSED / "transfers_clean.csv", index=False)
    views["units"].to_csv(PROCESSED / "units_clean.csv", index=False)
    print(f"Inspected {report['records_inspected']:,} records across {report['files_inspected']} CSV files.")
    print(f"Wrote a quality report, SHA-256 data manifest and 4 safe analytical views to {PROCESSED}.")
    print("Raw source files were not modified.")


if __name__ == "__main__":
    main()
