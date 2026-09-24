#!/usr/bin/env bash
# Reproduces the numbers behind:
# https://botmonster.com/web-dev/the-best-object-storage-for-saas-in-2026/
# Prices three SaaS workloads on eight providers.
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

banner() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }
note()   { printf '\033[36m%s\033[0m\n' "$1"; }

command -v python3 >/dev/null || { echo "python3 is required: sudo apt-get install -y python3"; exit 1; }
mkdir -p results

banner "Monthly cost of three SaaS workloads on eight providers"
python3 cost.py | tee results/cost.md

banner "Done"
note "Cost table: results/cost.md"
echo
echo "Post: https://botmonster.com/web-dev/the-best-object-storage-for-saas-in-2026/"
