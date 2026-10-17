#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -e '.[dev]'
fi
.venv/bin/python scripts/import_lcl_feather.py data_seed/df_2011.feather -o runs/lcl-2011 --work runs/shards-2011 --value-unit kWh
.venv/bin/oed scan runs/lcl-2011
.venv/bin/oed report runs/lcl-2011
.venv/bin/oed bench runs/lcl-2011 --task forecast
open runs/lcl-2011/quality-report.html
