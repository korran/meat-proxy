#!/usr/bin/env bash
# Lay a transparent graphics overlay (e.g. news_overlay.py's FFV1 .mkv) over a rendered shot and
# add the song for that stretch.
#
#   video/composite.sh SHOT OVERLAY SONG_START DURATION OUT.mp4 [crf]
#   e.g. video/composite.sh video/build/news_bridge_preview.mp4 video/build/news_overlay_bridge.mkv \
#            129.4 19.2 video/build/news_bridge_preview_audio.mp4
#
# Both inputs are renumbered frame by frame at 60 fps before overlaying: Blender's MKV stores
# timestamps to the millisecond (16 or 17 ms apart), and matching frames by those makes ffmpeg
# repeat every third overlay frame (a 40 fps stutter).
set -euo pipefail
cd "$(dirname "$0")/.."
SHOT=${1:?shot video}
OVER=${2:?overlay video}
START=${3:?song start seconds}
DUR=${4:?duration seconds}
OUT=${5:?output mp4}
CRF=${6:-18}
ffmpeg -hide_banner -loglevel error -y -i "$SHOT" -i "$OVER" \
  -ss "$START" -t "$DUR" -i assets/audio/we_need_a_meat_proxy.wav \
  -filter_complex "[0]setpts=N/(60*TB)[b];[1]setpts=N/(60*TB)[o];[b][o]overlay=eof_action=pass[v]" \
  -map "[v]" -map 2:a -r 60 -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p \
  -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
echo "$OUT"
