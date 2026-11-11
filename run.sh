#!/usr/bin/env bash
set -euo pipefail
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m scripts.prepare_data
python -m scripts.evaluate_forecast
exec streamlit run app.py --server.address 127.0.0.1 --server.port 8501
