#!/usr/bin/env bash
set -euo pipefail

pnpm -C apps/dashboard lint
pnpm -C apps/dashboard typecheck
uv -C services/api run pytest -q --cov
uv -C services/engine run pytest -q --cov
