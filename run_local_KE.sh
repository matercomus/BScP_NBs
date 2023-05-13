#!/bin/sh
docker run \
  --name knowledge_engine \
  --rm \
  -p 8280:8280 \
  ghcr.io/tno/knowledge-engine/smart-connector:1.1.3