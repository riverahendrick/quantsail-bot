#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../docker"
docker compose up -d
