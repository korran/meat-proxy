#!/usr/bin/env bash
# Render a stretch of the lyric video and mux it with the song audio.
#
#   video/render_clip.sh START END OUT.mp4 [extra build_video.py args...]
#
# START/END are seconds into the song's WAV. Frames go to video/build/frames.
set -euo pipefail
cd "$(dirname "$0")/.."

START=${1:?start seconds}
END=${2:?end seconds}
OUT=${3:?output mp4}
shift 3
FPS=60
for ((i = 1; i <= $#; i++)); do
  if [[ ${!i} == --fps ]]; then j=$((i + 1)); FPS=${!j}; fi
done

mkdir -p video/build
tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --format json > video/build/lyrics.json
rm -rf video/build/frames && mkdir -p video/build/frames
blender -b --factory-startup --python video/build_video.py -- \
  --json video/build/lyrics.json --start "$START" --end "$END" --out video/build/frames "$@"
mux() {
  ffmpeg -hide_banner -loglevel error -y \
    -framerate "$FPS" -start_number 1 -i video/build/frames/f_%04d.png \
    -ss "$START" -to "$END" -i assets/audio/we_need_a_meat_proxy.wav \
    -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -r "$FPS" \
    -c:a aac -b:a 320k -shortest -movflags +faststart "$OUT"
}
mux
echo "wrote $OUT"
