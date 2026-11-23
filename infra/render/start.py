"""Compose private service addresses supplied by a Render Blueprint."""

import os

from cloudeq.platform.server import main

if os.environ.get("MONGODB_HOSTPORT"):
    os.environ["MONGODB_URI"] = "mongodb://" + os.environ["MONGODB_HOSTPORT"]
if os.environ.get("KAFKA_HOSTPORT"):
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = os.environ["KAFKA_HOSTPORT"]

raise SystemExit(main(["--host", "0.0.0.0", "--port", os.environ.get("PORT", "10000")]))
