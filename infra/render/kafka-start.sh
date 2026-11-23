#!/bin/bash
set -euo pipefail
export KAFKA_ADVERTISED_LISTENERS="PLAINTEXT://${RENDER_INTERNAL_HOSTNAME:?}:9092"
exec /etc/kafka/docker/run
