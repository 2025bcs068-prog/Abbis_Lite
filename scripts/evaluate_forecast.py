"""Run a rolling-origin forecast comparison on a reproducible default scenario."""
import json
from pathlib import Path

from abbis.engine import RAW_DIR, forecast_backtest, load_frames

ROOT = Path(__file__).resolve().parents[1]


def main():
    frames = load_frames(RAW_DIR)
    result = forecast_backtest(frames, "HSP-018", "RBC", "A+")
    out = ROOT / "data" / "processed" / "forecast_evaluation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in result.items() if k != "series"}
    out.write_text(json.dumps(safe, indent=2), encoding="utf-8")
    if "error" in result:
        print(result["error"])
        return
    print("Rolling-origin forecast evaluation: HSP-018 · A+ · RBC")
    for name, metrics in result["metrics"].items():
        print(f"{name:26} WAPE={metrics['WAPE']}  MAE={metrics['MAE']}")
    print("Selected:", result["selected_model"])
    print("Saved:", out)


if __name__ == "__main__":
    main()
