#!/bin/sh
# Rebuild junction.net.xml from the plain-XML sources (headless).
cd "$(dirname "$0")"
NETCONVERT=$(python3 -c "from africot.sumo_utils import sumo_binary; print(sumo_binary('netconvert'))" 2>/dev/null || echo netconvert)
"$NETCONVERT" -n junction.nod.xml -e junction.edg.xml -x junction.con.xml \
  --crossings.guess true --walkingareas true --no-turnarounds true \
  --lefthand false --tls.default-type static \
  --default.lanewidth 3.5 \
  -o junction.net.xml
