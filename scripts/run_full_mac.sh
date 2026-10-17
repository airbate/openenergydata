#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
SOURCE_DIR="${1:-/Volumes/Ventoy/data_lcl}"
RECOVERY_DIR="${2:-runs/recovered-source}"
mkdir -p "$RECOVERY_DIR"
if [ -f "$RECOVERY_DIR/df_2013.feather" ] && [ ! -f "$RECOVERY_DIR/df_2013.recovery.json" ]; then
  echo "Recovery audit missing; choose a new recovery directory before retrying." >&2
  exit 1
fi
if [ ! -f "$RECOVERY_DIR/df_2013.feather" ]; then
  .venv/bin/python scripts/recover_truncated_feather.py "$SOURCE_DIR/df_2013.feather" "$RECOVERY_DIR/df_2013.feather"
fi
.venv/bin/python scripts/import_lcl_feather.py data_seed/df_2011.feather "$RECOVERY_DIR/df_2013.feather" "$SOURCE_DIR/df_2014.feather" -o runs/lcl-original-ids-partial --work runs/temp-shards
.venv/bin/python scripts/import_lcl_feather.py "$SOURCE_DIR/df_2012.feather" --encoded-id-prefix encoded2012_ -o runs/lcl-2012-encoded --work runs/temp-shards
for dataset in runs/lcl-original-ids-partial runs/lcl-2012-encoded; do
  .venv/bin/oed report "$dataset"
  .venv/bin/oed bench "$dataset" --task forecast
done
