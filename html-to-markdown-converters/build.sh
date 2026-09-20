#!/usr/bin/env bash
# Builds the benchmark image with every version from versions.env as a build arg.
# run.sh calls this; it is separate so you can rebuild without running stages.
set -euo pipefail
cd "$(dirname "$0")"
TAG="${1:-html2md-bench:pinned}"
set -a; . ./versions.env; set +a
args=()
while IFS='=' read -r k _; do
  [ -n "$k" ] || continue
  case "$k" in \#*) continue ;; esac
  args+=(--build-arg "$k=${!k}")
done < versions.env
exec docker build "${args[@]}" -t "$TAG" .
