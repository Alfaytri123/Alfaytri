#!/usr/bin/env bash
# Full render of the ad: picture -> audio -> mux -> QC -> storyboard.
# Usage: scripts/build.sh WORKDIR   (WORKDIR holds clips/, fonts/, config/, scripts/)
set -euo pipefail
W="$(cd "${1:-.}" && pwd)"
OUT="$W/output/heat-to-comfort_9x16_1080x1920.mp4"

python3 "$W/scripts/brand_logo.py" "$W"   # interim logo PNGs (skipped in effect once logo_path points at the official file)
python3 "$W/scripts/compose.py" "$W"
python3 "$W/scripts/audio_design.py" "$W"
mkdir -p "$W/output"
ffmpeg -v error -y -i "$W/build/picture.mp4" -i "$W/audio/mix.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -ac 2 \
  -shortest -movflags +faststart \
  -metadata title="من الحر إلى الراحة" -metadata comment="AC maintenance ad, 9:16" "$OUT"
python3 "$W/scripts/qc.py" "$W" "$OUT"
python3 "$W/scripts/storyboard.py" "$W" "$OUT"
echo "built $OUT"
