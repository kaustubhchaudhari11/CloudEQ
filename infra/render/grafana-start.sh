#!/bin/sh
set -eu
mkdir -p /tmp/forge-dashboards
sed "s|http://app:8000|http://${FORGE_API_HOSTPORT:?}|g" \
  /var/lib/forge-dashboards/forge-span.json > /tmp/forge-dashboards/forge-span.json
exec /run.sh
