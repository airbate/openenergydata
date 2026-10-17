#!/usr/bin/env bash
# 后台下载 REDD low_freq（约 660MB）。多源依次尝试，成功即停。
set -u
DEST="${1:-/home/airbate/datasets/redd}"
mkdir -p "$DEST"; cd "$DEST"
SOURCES=(
  "http://redd.csail.mit.edu/data/low_freq.tar.bz2"
  "https://redd.csail.mit.edu/data/low_freq.tar.bz2"
)
for url in "${SOURCES[@]}"; do
  echo "[$(date +%H:%M:%S)] trying $url"
  if curl -fL --connect-timeout 20 --retry 3 -C - -o low_freq.tar.bz2 "$url"; then
    echo "[$(date +%H:%M:%S)] download OK, verifying..."
    if bzip2 -t low_freq.tar.bz2 2>/dev/null; then
      echo "[$(date +%H:%M:%S)] archive valid, extracting..."
      tar -xjf low_freq.tar.bz2 && echo "DONE: $DEST/low_freq" && exit 0
    fi
    echo "archive corrupt, trying next source"
  fi
done
echo "ALL SOURCES FAILED - try OpenDataLab manual download later"
exit 1
