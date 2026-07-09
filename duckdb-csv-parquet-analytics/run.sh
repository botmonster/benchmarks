#!/usr/bin/env bash
# Reproduces the benchmarks behind:
# https://botmonster.com/coding/duckdb-developers-analyze-csv-parquet-no-server/
# Downloads NYC TLC taxi data (if absent), installs a pinned DuckDB CLI plus a
# uv venv (pandas/polars/duckdb), and runs four guided stages. Nothing touches
# your system: tools go in ./.tools, data in ./data. See README.md for flags.
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

DUCKDB_VERSION="1.5.4"
PANDAS_VERSION="2.2.3"
POLARS_VERSION="1.17.1"
PYARROW_VERSION="18.1.0"

# NYC TLC yellow taxi, stable historical months. Small = 3 months (~10M rows),
# full = all of 2024 (~40M rows).
YEAR="2024"
MONTHS_SMALL="01 02 03"
MONTHS_FULL="01 02 03 04 05 06 07 08 09 10 11 12"
CDN="https://d37ci6vzurychx.cloudfront.net"

YES=0
LATEST=0
FULL=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --latest) LATEST=1 ;;
    --full) FULL=1 ;;
    *) echo "usage: $0 [--yes] [--latest] [--full]"; exit 1 ;;
  esac
done

TOOLS="$PWD/.tools"
DATA="$PWD/data"
REPS=5

banner() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }
note()   { printf '\033[36m%s\033[0m\n' "$1"; }
warn()   { printf '\033[33mWARN: %s\033[0m\n' "$1"; }

stage_gate() {
  banner "$1"
  [ "$YES" = 1 ] && return 0
  local a
  read -r -p "Press Enter to run this stage, or s+Enter to skip: " a
  [ "$a" != "s" ]
}

# ---------- preflight ----------
banner "Preflight"
[ "$(uname -s)/$(uname -m)" = "Linux/x86_64" ] || { echo "This script targets Linux x86_64."; exit 1; }
missing=""
for c in curl unzip python3 uv; do
  command -v "$c" >/dev/null || missing="$missing $c"
done
if [ -n "$missing" ]; then
  echo "Missing tools:$missing"
  echo "Install: sudo apt-get install -y curl unzip python3 ; and uv from https://docs.astral.sh/uv/"
  exit 1
fi
NCPU=$(nproc)
MEMGB=$(awk '/MemTotal/{printf "%.0f", $2/1024/1024}' /proc/meminfo)
note "CPUs: $NCPU  RAM: ${MEMGB}GB"

# ---------- tool bootstrap ----------
banner "Tool bootstrap (everything goes into ./.tools, nothing touches your system)"
mkdir -p "$TOOLS/bin" "$DATA"

if [ "$LATEST" = 1 ]; then
  note "--latest: resolving newest DuckDB CLI release ..."
  DUCKDB_VERSION=$(python3 -c "
import json,urllib.request
d=json.load(urllib.request.urlopen('https://api.github.com/repos/duckdb/duckdb/releases/latest'))
print(d['tag_name'].lstrip('v'))
")
  note "newest DuckDB is $DUCKDB_VERSION; python libs will resolve to newest too."
fi

DUCKDB_BIN="$TOOLS/bin/duckdb"
if [ ! -x "$DUCKDB_BIN" ] || [ "$("$DUCKDB_BIN" --version 2>/dev/null | grep -o "v$DUCKDB_VERSION" || true)" = "" ]; then
  note "Downloading DuckDB CLI v$DUCKDB_VERSION ..."
  curl -fL -o "$TOOLS/duckdb.zip" \
    "https://github.com/duckdb/duckdb/releases/download/v$DUCKDB_VERSION/duckdb_cli-linux-amd64.zip"
  unzip -o "$TOOLS/duckdb.zip" -d "$TOOLS/bin" >/dev/null
  rm -f "$TOOLS/duckdb.zip"
fi

VENV="$TOOLS/venv"
PY="$VENV/bin/python"
if [ ! -x "$PY" ]; then
  note "Creating uv venv with pandas/polars/duckdb ..."
  uv venv "$VENV" >/dev/null
  if [ "$LATEST" = 1 ]; then
    uv pip install --python "$PY" duckdb pandas polars pyarrow >/dev/null
  else
    uv pip install --python "$PY" \
      "duckdb==$DUCKDB_VERSION" "pandas==$PANDAS_VERSION" \
      "polars==$POLARS_VERSION" "pyarrow==$PYARROW_VERSION" >/dev/null
  fi
fi

printf '\n%-10s %s\n' "duckdb-cli" "$("$DUCKDB_BIN" --version)"
"$PY" - <<'EOF'
import duckdb, pandas, polars, pyarrow
print(f"{'py-duckdb':<10} {duckdb.__version__}")
print(f"{'pandas':<10} {pandas.__version__}")
print(f"{'polars':<10} {polars.__version__}")
print(f"{'pyarrow':<10} {pyarrow.__version__}")
EOF

# ---------- data download ----------
banner "Dataset (NYC TLC yellow taxi + taxi zone lookup)"
if [ "$FULL" = 1 ]; then MONTHS="$MONTHS_FULL"; else MONTHS="$MONTHS_SMALL"; fi
note "Downloading months: $YEAR-[$MONTHS] (skip any already present)"
for m in $MONTHS; do
  f="$DATA/yellow_tripdata_$YEAR-$m.parquet"
  if [ ! -f "$f" ]; then
    note "  fetch $YEAR-$m ..."
    curl -fL -o "$f" "$CDN/trip-data/yellow_tripdata_$YEAR-$m.parquet"
  fi
done
if [ ! -f "$DATA/taxi_zone_lookup.csv" ]; then
  curl -fL -o "$DATA/taxi_zone_lookup.csv" "$CDN/misc/taxi_zone_lookup.csv"
fi
GLOB="$DATA/yellow_tripdata_$YEAR-*.parquet"
ZONES="$DATA/taxi_zone_lookup.csv"
du -ch $GLOB "$ZONES" | tail -1 | awk '{print "Dataset on disk: "$1}'

# ---------- stage 1: direct query, no import ----------
if stage_gate "Stage 1/4: Direct query on Parquet, no import step (CLI)"; then
  note "Pointing the DuckDB CLI straight at the Parquet glob, zero CREATE TABLE:"
  START=$(python3 -c 'import time;print(time.time())')
  "$DUCKDB_BIN" -c "
    SELECT count(*) AS trips,
           round(avg(fare_amount),2) AS avg_fare,
           round(avg(trip_distance),2) AS avg_miles
    FROM read_parquet('$GLOB');"
  END=$(python3 -c 'import time;print(time.time())')
  python3 -c "print(f'wall: {$END-$START:.2f}s')"
fi

# ---------- stage 2: DuckDB vs Pandas vs Polars ----------
if stage_gate "Stage 2/4: DuckDB vs Pandas vs Polars (filter / group-by / join)"; then
  "$PY" bench_compare.py "$GLOB" "$ZONES" "$REPS" "results/compare.json"
fi

# ---------- stage 3: CSV vs Parquet scan ----------
if stage_gate "Stage 3/4: CSV vs Parquet scan on identical data (pushdown)"; then
  ONE=$(ls $GLOB | head -1)
  CSVFILE="$DATA/$(basename "${ONE%.parquet}").csv"
  if [ ! -f "$CSVFILE" ]; then
    note "Materializing a CSV copy of $(basename "$ONE") ..."
    "$DUCKDB_BIN" -c "COPY (SELECT * FROM read_parquet('$ONE')) TO '$CSVFILE' (FORMAT CSV, HEADER);"
  fi
  du -h "$ONE" "$CSVFILE" | awk '{print $1"\t"$2}'
  "$PY" bench_scan.py "$ONE" "$CSVFILE" "$REPS"
fi

# ---------- stage 4: out-of-core under a tight memory_limit ----------
if stage_gate "Stage 4/4: Out-of-core aggregation under a 2GB memory_limit"; then
  "$PY" bench_outofcore.py "$GLOB" "2GB"
  rm -rf "$DATA/duckdb_spill"
fi

banner "Done"
note "Raw comparison JSON: results/compare.json"
