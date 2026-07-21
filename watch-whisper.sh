#!/bin/sh
# Poll the whisper-cache volume until small.pt is fully downloaded (~461 MB).
i=0
size=0
while [ $i -lt 90 ]; do
  size=$(docker run --rm -v ai-screen-assistant_whisper-cache:/c busybox stat -c %s /c/small.pt 2>/dev/null || echo 0)
  if [ "$size" -ge 460000000 ]; then
    echo "DOWNLOAD-COMPLETE size=$size"
    exit 0
  fi
  echo "progress size=$size"
  sleep 20
  i=$((i + 1))
done
echo "TIMEOUT last-size=$size"
exit 1
