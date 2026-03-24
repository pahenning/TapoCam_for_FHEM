#!/bin/bash

OUT="/opt/fhem/www/images/Tapo.jpg"
URL="/fhem/images/Tapo.jpg"

ffmpeg -rtsp_transport tcp -y \
  -i "rtsp://phenning:test1234@192.168.0.93:554/stream1" \
  -frames:v 1 "$OUT" >/dev/null 2>&1

if [ $? -eq 0 ] && [ -s "$OUT" ]; then
  echo "$URL"
else
  echo "error creating image"
fi
