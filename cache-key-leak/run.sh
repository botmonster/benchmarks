#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

NGINX_VERSION="1.30.4"

YES=0
LATEST=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --latest) LATEST=1 ;;
    *) echo "usage: $0 [--yes] [--latest]"; exit 1 ;;
  esac
done

TOOLS="$PWD/.tools"
RUN="$TOOLS/run"
RESULTS="$PWD/results"
URL="http://127.0.0.1:18080/v1/devices"

banner() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }
note()   { printf '\033[36m%s\033[0m\n' "$1"; }

stage_gate() {
  banner "$1"
  [ "$YES" = 1 ] && return 0
  local a
  read -r -p "Press Enter to run this stage, or s+Enter to skip: " a
  [ "$a" != "s" ]
}

ORIGIN_PID=""
stop_all() {
  if [ -f "$RUN/logs/nginx.pid" ]; then
    kill "$(cat "$RUN/logs/nginx.pid")" 2>/dev/null || true
    rm -f "$RUN/logs/nginx.pid"
  fi
  if [ -n "$ORIGIN_PID" ]; then
    kill "$ORIGIN_PID" 2>/dev/null || true
    wait "$ORIGIN_PID" 2>/dev/null || true
    ORIGIN_PID=""
  fi
  sleep 0.5
}
trap stop_all EXIT

start_stack() {
  local conf="$1" private="${2:-0}"
  stop_all
  rm -rf "$RUN"
  mkdir -p "$RUN/logs" "$RUN/conf" "$RUN/cache"
  cp "$conf" "$RUN/conf/nginx.conf"
  : > "$RUN/origin-hits.log"
  ORIGIN_PRIVATE="$private" ORIGIN_LOG="$RUN/origin-hits.log" python3 origin.py 2>/dev/null &
  ORIGIN_PID=$!
  for _ in $(seq 1 50); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18081/v1/devices)" = "401" ] && break
    sleep 0.1
  done
  "$NGINX_BIN" -p "$RUN" -c conf/nginx.conf -e logs/error.log
  sleep 0.3
}

ask() {
  local who="$1" out="$2" raw="$3"
  local resp account status
  resp=$(curl -s -D - -H "Authorization: Bearer token-$who" "$URL")
  printf '### %s: GET /v1/devices with Authorization: Bearer token-%s\n%s\n\n' "$who" "$who" "$resp" >> "$raw"
  status=$(printf '%s' "$resp" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-cache-status"{print $2}')
  account=$(printf '%s' "$resp" | tail -n1 | python3 -c 'import json,sys;print(json.load(sys.stdin)["account"])')
  local verdict="own doors"
  [ "$account" != "$who" ] && verdict="LEAK: ${account}'s doors"
  printf '%-6s asks -> %-24s (X-Cache-Status: %s)\n' "$who" "$verdict" "$status" | tee -a "$out"
}

origin_hits() {
  local out="$1"
  printf 'origin log:\n' | tee -a "$out"
  sed 's/^/  /' "$RUN/origin-hits.log" | tee -a "$out"
}

banner "Preflight"
[ "$(uname -s)" = "Linux" ] || { echo "This script targets Linux."; exit 1; }
missing=""
for c in curl gcc make tar python3; do
  command -v "$c" >/dev/null || missing="$missing $c"
done
if [ -n "$missing" ]; then
  echo "Missing tools:$missing"
  echo "Install: sudo apt-get install -y curl build-essential python3"
  exit 1
fi
note "python3: $(python3 --version)"

banner "Tool bootstrap (nginx is built from source into ./.tools, nothing touches your system)"
mkdir -p "$TOOLS" "$RESULTS"
if [ "$LATEST" = 1 ]; then
  NGINX_VERSION=$(curl -s https://nginx.org/en/download.html | python3 -c '
import re,sys
page=sys.stdin.read()
stable=page.split("Stable version",1)[1]
print(re.search(r"nginx-(\d+\.\d+\.\d+)\.tar\.gz",stable).group(1))')
  note "--latest: newest stable nginx is $NGINX_VERSION"
fi
NGINX_DIR="$TOOLS/nginx-$NGINX_VERSION"
NGINX_BIN="$NGINX_DIR/sbin/nginx"
if [ ! -x "$NGINX_BIN" ]; then
  note "Downloading and building nginx $NGINX_VERSION (about a minute) ..."
  curl -fsSL -o "$TOOLS/nginx.tar.gz" "https://nginx.org/download/nginx-$NGINX_VERSION.tar.gz"
  rm -rf "$TOOLS/src" && mkdir -p "$TOOLS/src"
  tar -xzf "$TOOLS/nginx.tar.gz" -C "$TOOLS/src"
  (
    cd "$TOOLS/src/nginx-$NGINX_VERSION"
    ./configure --prefix="$NGINX_DIR" \
      --without-http_rewrite_module --without-http_gzip_module >/dev/null
    make -j"$(nproc)" >/dev/null
    make install >/dev/null
  )
  rm -rf "$TOOLS/src" "$TOOLS/nginx.tar.gz"
fi
"$NGINX_BIN" -v

if stage_gate "Stage 1/4: default cache key, 300 s TTL (the leak)"; then
  OUT="$RESULTS/stage1-leak.txt"; RAW="$RESULTS/stage1-leak-raw.txt"
  : > "$OUT"; : > "$RAW"
  start_stack nginx/leak.conf
  note "proxy_cache on, proxy_cache_valid 200 300s, proxy_cache_key left at its default:"
  for who in alice bob carol alice; do ask "$who" "$OUT" "$RAW"; done
  origin_hits "$OUT"
fi

if stage_gate "Stage 2/4: many clients polling the leaky cache (TTL scaled to 5 s)"; then
  OUT="$RESULTS/stage2-poll-sim.txt"
  CONF="$TOOLS/leak-5s.conf"
  sed 's/proxy_cache_valid 200 300s;/proxy_cache_valid 200 5s;/' nginx/leak.conf > "$CONF"
  start_stack "$CONF"
  note "40 clients, each polling about every 1 s for 90 s. The 1 s poll stands in for Home Assistant's 15 s poll, the 5 s TTL for API Gateway's 300 s."
  python3 poll_sim.py --clients 40 --interval 1 --jitter 0.2 --duration 90 --csv "$RESULTS/poll-sim.csv" | tee "$OUT"
fi

if stage_gate "Stage 3/4: fix one, put the Authorization header in the cache key"; then
  OUT="$RESULTS/stage3-fix-key.txt"; RAW="$RESULTS/stage3-fix-key-raw.txt"
  : > "$OUT"; : > "$RAW"
  start_stack nginx/fixed-key.conf
  note "proxy_cache_key \$scheme\$proxy_host\$request_uri\$http_authorization:"
  for who in alice bob carol alice; do ask "$who" "$OUT" "$RAW"; done
  origin_hits "$OUT"
fi

if stage_gate "Stage 4/4: fix two, origin sends Cache-Control: private"; then
  OUT="$RESULTS/stage4-fix-private.txt"; RAW="$RESULTS/stage4-fix-private-raw.txt"
  : > "$OUT"; : > "$RAW"
  start_stack nginx/leak.conf 1
  note "Same leaky nginx config as stage 1, but the origin marks per-user responses private:"
  for who in alice bob carol alice; do ask "$who" "$OUT" "$RAW"; done
  origin_hits "$OUT"
fi

banner "Done"
note "Results written to $RESULTS"
