#!/usr/bin/env bash
# Reproduces the benchmarks behind:
# https://botmonster.com/web-dev/bun-vs-deno-vs-nodejs-javascript-runtime-2026/
# Installs pinned runtimes into ./.tools (no sudo, no system changes) and runs
# six guided stages. See README.md for methodology and flags.
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

NODE_VERSION="24.18.0"
BUN_VERSION="1.3.14"
DENO_VERSION="2.9.1"
OHA_VERSION="1.14.0"

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
TMP="$(mktemp -d /tmp/runtime-bench.XXXXXX)"
SERVER_PID=""
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT

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

now_ms() { echo $(( $(date +%s%N) / 1000000 )); }

median() {
  printf '%s\n' "$@" | sort -n | awk '{v[NR]=$1} END{print v[int((NR+1)/2)]}'
}

# ---------- preflight ----------
banner "Preflight"
[ "$(uname -s)/$(uname -m)" = "Linux/x86_64" ] || { echo "This script targets Linux x86_64."; exit 1; }
missing=""
for c in curl unzip xz taskset lscpu python3 ss; do
  command -v "$c" >/dev/null || missing="$missing $c"
done
if [ -n "$missing" ]; then
  echo "Missing tools:$missing"
  echo "Install them with: sudo apt-get install -y curl unzip xz-utils util-linux python3 iproute2"
  exit 1
fi
for p in 3001 3002 3003; do
  if ss -tln | grep -q ":$p "; then echo "Port $p is in use, free it first."; exit 1; fi
done

NCPU=$(nproc)
SRV_PIN=""
CLI_PIN=""
if [ "$NCPU" -ge 4 ]; then
  # keep core 0 (and its SMT sibling) exclusive to the server; client gets the rest
  siblings=$(cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list)
  CLIENT_CORES=$(python3 -c "
excl=set()
for part in '$siblings'.split(','):
    if '-' in part:
        a,b=part.split('-'); excl.update(range(int(a),int(b)+1))
    else:
        excl.add(int(part))
print(','.join(str(c) for c in range($NCPU) if c not in excl))
")
  SRV_PIN="taskset -c 0"
  CLI_PIN="taskset -c $CLIENT_CORES"
  note "Cores: $NCPU. Server pinned to core 0 (siblings: $siblings), client on: $CLIENT_CORES"
else
  warn "Only $NCPU CPUs: running unpinned. Throughput numbers may be client-bound and unreliable."
fi
governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)
note "CPU governor: $governor (identical for all three runtimes, so relative results hold)"

# ---------- tool bootstrap ----------
banner "Tool bootstrap (everything goes into ./.tools, nothing touches your system)"
mkdir -p "$TOOLS/bin"

if [ "$LATEST" = 1 ]; then
  NODE_VERSION=$(python3 -c "
import json,urllib.request
data=json.load(urllib.request.urlopen('https://nodejs.org/dist/index.json'))
print(next(e['version'] for e in data if e.get('lts')).lstrip('v'))
")
  note "--latest: newest Node LTS is $NODE_VERSION; Bun and Deno installers will fetch their newest releases."
fi

NODE_DIR="$TOOLS/node-v$NODE_VERSION-linux-x64"
if [ ! -x "$NODE_DIR/bin/node" ]; then
  note "Downloading Node.js v$NODE_VERSION ..."
  curl -fL "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz" | tar -xJ -C "$TOOLS"
fi
NODE_BIN="$NODE_DIR/bin/node"

if [ ! -x "$TOOLS/bun/bin/bun" ]; then
  note "Installing Bun ..."
  if [ "$LATEST" = 1 ]; then
    curl -fsSL https://bun.sh/install | BUN_INSTALL="$TOOLS/bun" bash >/dev/null
  else
    curl -fsSL https://bun.sh/install | BUN_INSTALL="$TOOLS/bun" bash -s "bun-v$BUN_VERSION" >/dev/null
  fi
fi
BUN_BIN="$TOOLS/bun/bin/bun"

if [ ! -x "$TOOLS/deno/bin/deno" ]; then
  note "Installing Deno ..."
  if [ "$LATEST" = 1 ]; then
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL="$TOOLS/deno" sh -s -- --yes >/dev/null
  else
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL="$TOOLS/deno" sh -s -- --yes "v$DENO_VERSION" >/dev/null
  fi
fi
DENO_BIN="$TOOLS/deno/bin/deno"

if [ ! -x "$TOOLS/bin/oha" ]; then
  note "Downloading oha v$OHA_VERSION (Rust load generator) ..."
  curl -fL -o "$TOOLS/bin/oha" "https://github.com/hatoo/oha/releases/download/v$OHA_VERSION/oha-linux-amd64"
  chmod +x "$TOOLS/bin/oha"
fi
OHA="$TOOLS/bin/oha"

printf '\n%-10s %s\n' "node" "$("$NODE_BIN" --version)"
printf '%-10s %s\n'   "bun"  "$("$BUN_BIN" --version)"
printf '%-10s %s\n'   "deno" "$("$DENO_BIN" --version | head -1)"
printf '%-10s %s\n'   "oha"  "$("$OHA" --version)"

R_THRU_NODE="skipped"; R_THRU_BUN="skipped"; R_THRU_DENO="skipped"; R_SAT="skipped"
R_COLD_NODE="skipped"; R_COLD_BUN="skipped"; R_COLD_DENO="skipped"
R_JSON_NODE="skipped"; R_JSON_BUN="skipped"; R_JSON_DENO="skipped"
R_INST_NPM_COLD="skipped"; R_INST_NPM_WARM="skipped"
R_INST_BUN_COLD="skipped"; R_INST_BUN_WARM="skipped"
R_INST_DENO_COLD="skipped"; R_INST_DENO_WARM="skipped"
R_TEST_JEST="skipped"; R_TEST_BUN="skipped"; R_TEST_NODE="skipped"; R_TEST_DENO="skipped"
R_RSS_NODE="skipped"; R_RSS_BUN="skipped"; R_RSS_DENO="skipped"

wait_port() {
  for _ in $(seq 1 50); do
    curl -s --max-time 1 "http://localhost:$1/" >/dev/null 2>&1 && return 0
    sleep 0.2
  done
  echo "Server on port $1 did not come up."; return 1
}

oha_rps() {
  # shellcheck disable=SC2086
  local out; out=$($CLI_PIN "$OHA" -z "$1" -c "$2" --no-tui "http://localhost:$3/" 2>&1)
  local ok; ok=$(echo "$out" | awk '/Success rate/ {print $3}')
  [ "$ok" = "100.00%" ] || warn "success rate $ok on port $3"
  echo "$out" | awk '/Requests\/sec/ {printf "%.0f", $2}'
}

start_server() {
  # shellcheck disable=SC2086
  $SRV_PIN "$@" >/dev/null 2>&1 &
  SERVER_PID=$!
}

stop_server() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
}

# ---------- stage 1: HTTP throughput ----------
if stage_gate "Stage 1/6: HTTP throughput (single core, ~3 min)"; then
  for rt in node bun deno; do
    case "$rt" in
      node) start_server "$NODE_BIN" server-node.js; port=3001 ;;
      bun)  start_server "$BUN_BIN"  server-bun.js;  port=3002 ;;
      deno) start_server "$DENO_BIN" run --allow-net server-deno.js; port=3003 ;;
    esac
    wait_port "$port"
    oha_rps 4s 100 "$port" >/dev/null   # warmup
    p1=$(oha_rps 15s 200 "$port")
    p2=$(oha_rps 15s 200 "$port")
    avg=$(( (p1 + p2) / 2 ))
    note "$rt: pass1=$p1 pass2=$p2 avg=$avg req/s"
    case "$rt" in
      node) R_THRU_NODE=$avg ;;
      bun)  R_THRU_BUN=$avg ;;
      deno) R_THRU_DENO=$avg ;;
    esac
    stop_server
  done
  note "Saturation sanity check: two parallel clients against the same Bun server ..."
  start_server "$BUN_BIN" server-bun.js
  wait_port 3002
  oha_rps 3s 100 3002 >/dev/null
  oha_rps 8s 100 3002 >"$TMP/sat1" &
  satpid=$!
  oha_rps 8s 100 3002 >"$TMP/sat2"
  wait "$satpid" || true
  stop_server
  sat_total=$(( $(cat "$TMP/sat1") + $(cat "$TMP/sat2") ))
  R_SAT="two clients: $sat_total req/s combined vs $R_THRU_BUN single"
  if [ "$R_THRU_BUN" != "skipped" ] && [ "$sat_total" -gt $(( R_THRU_BUN * 115 / 100 )) ]; then
    warn "Combined throughput of two clients exceeds one client by >15%."
    warn "Your load generator was the bottleneck; single-client numbers above are a floor, not the truth."
  else
    note "Saturation check passed: the server, not the client, was the bottleneck."
  fi
fi

# ---------- stage 2: cold start ----------
if stage_gate "Stage 2/6: process cold start (15 runs each)"; then
  for rt in node bun deno; do
    case "$rt" in
      node) cmd=("$NODE_BIN" hello.js) ;;
      bun)  cmd=("$BUN_BIN" run hello.js) ;;
      deno) cmd=("$DENO_BIN" run hello.js) ;;
    esac
    "${cmd[@]}" >/dev/null 2>&1   # warm the file cache
    times=()
    for _ in $(seq 1 15); do
      t0=$(now_ms)
      "${cmd[@]}" >/dev/null 2>&1
      times+=( $(( $(now_ms) - t0 )) )
    done
    med=$(median "${times[@]}")
    note "$rt: median ${med} ms"
    case "$rt" in
      node) R_COLD_NODE="$med ms" ;;
      bun)  R_COLD_BUN="$med ms" ;;
      deno) R_COLD_DENO="$med ms" ;;
    esac
  done
fi

# ---------- stage 3: JSON parse/stringify ----------
if stage_gate "Stage 3/6: JSON.parse / JSON.stringify (3.3 MB payload)"; then
  # shellcheck disable=SC2086
  R_JSON_NODE=$($SRV_PIN "$NODE_BIN" json-bench.js)
  # shellcheck disable=SC2086
  R_JSON_BUN=$($SRV_PIN "$BUN_BIN" run json-bench.js)
  # shellcheck disable=SC2086
  R_JSON_DENO=$($SRV_PIN "$DENO_BIN" run json-bench.js)
  note "node: $R_JSON_NODE"
  note "bun:  $R_JSON_BUN"
  note "deno: $R_JSON_DENO"
fi

# ---------- stage 4: install speed ----------
PROJ="$TMP/install-bench"
if stage_gate "Stage 4/6: package install, cold + warm caches (downloads ~100 MB from npm)"; then
  mkdir -p "$PROJ"
  cp install-bench/package.json "$PROJ/"
  export npm_config_cache="$TMP/npm-cache"
  export BUN_INSTALL_CACHE_DIR="$TMP/bun-cache"
  export DENO_DIR="$TMP/deno-dir"
  export PATH="$NODE_DIR/bin:$PATH"

  timed() { local t0; t0=$(now_ms); "$@" >/dev/null 2>&1; echo "$(( $(now_ms) - t0 ))"; }

  cd "$PROJ"
  ms=$(timed "$BUN_BIN" install);                              R_INST_BUN_COLD="$(awk "BEGIN{printf \"%.1f s\", $ms/1000}")"
  rm -rf node_modules
  ms=$(timed "$BUN_BIN" install);                              R_INST_BUN_WARM="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"
  note "bun:  cold $R_INST_BUN_COLD, warm $R_INST_BUN_WARM"

  rm -rf node_modules bun.lock bun.lockb
  ms=$(timed "$DENO_BIN" install);                             R_INST_DENO_COLD="$(awk "BEGIN{printf \"%.1f s\", $ms/1000}")"
  rm -rf node_modules
  ms=$(timed "$DENO_BIN" install);                             R_INST_DENO_WARM="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"
  note "deno: cold $R_INST_DENO_COLD, warm $R_INST_DENO_WARM (links from global cache, less disk work than npm/bun)"

  rm -rf node_modules deno.lock
  ms=$(timed npm install --no-audit --no-fund);                R_INST_NPM_COLD="$(awk "BEGIN{printf \"%.1f s\", $ms/1000}")"
  rm -rf node_modules
  ms=$(timed npm install --no-audit --no-fund);                R_INST_NPM_WARM="$(awk "BEGIN{printf \"%.1f s\", $ms/1000}")"
  note "npm:  cold $R_INST_NPM_COLD, warm $R_INST_NPM_WARM"
  cd - >/dev/null
fi

# ---------- stage 5: test runners ----------
if stage_gate "Stage 5/6: test runners (200 trivial tests across 20 files)"; then
  if [ ! -x "$PROJ/node_modules/.bin/jest" ]; then
    note "Materializing node_modules for jest ..."
    mkdir -p "$PROJ"; cp install-bench/package.json "$PROJ/"
    export BUN_INSTALL_CACHE_DIR="${BUN_INSTALL_CACHE_DIR:-$TMP/bun-cache}"
    (cd "$PROJ" && "$BUN_BIN" install >/dev/null 2>&1)
  fi
  mkdir -p "$PROJ/tests-jest" "$PROJ/tests-node" "$PROJ/tests-deno"
  for f in $(seq 1 20); do
    : > "$PROJ/tests-jest/f$f.test.js"
    printf "const { test } = require('node:test'); const assert = require('node:assert');\n" > "$PROJ/tests-node/f$f.test.js"
    : > "$PROJ/tests-deno/f${f}_test.js"
    for i in $(seq 1 10); do
      echo "test('f${f}t${i}', () => { expect(${i}+${i}).toBe($((i+i))); });" >> "$PROJ/tests-jest/f$f.test.js"
      echo "test('f${f}t${i}', () => { assert.strictEqual(${i}+${i}, $((i+i))); });" >> "$PROJ/tests-node/f$f.test.js"
      echo "Deno.test('f${f}t${i}', () => { if (${i}+${i} !== $((i+i))) throw new Error('fail'); });" >> "$PROJ/tests-deno/f${f}_test.js"
    done
  done

  export PATH="$NODE_DIR/bin:$PATH"
  cd "$PROJ"
  timed() { local t0; t0=$(now_ms); "$@" >/dev/null 2>&1; echo "$(( $(now_ms) - t0 ))"; }

  ./node_modules/.bin/jest tests-jest --silent >/dev/null 2>&1 || { echo "jest failed to run its suite"; exit 1; }
  ms=$(timed ./node_modules/.bin/jest tests-jest --silent);   R_TEST_JEST="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"

  "$BUN_BIN" test tests-jest >/dev/null 2>&1
  ms=$(timed "$BUN_BIN" test tests-jest);                     R_TEST_BUN="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"

  # explicit globs: a bare directory arg makes node --test run zero tests
  "$NODE_BIN" --test tests-node/*.test.js >/dev/null 2>&1
  ms=$(timed "$NODE_BIN" --test tests-node/*.test.js);        R_TEST_NODE="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"

  "$DENO_BIN" test tests-deno >/dev/null 2>&1
  ms=$(timed "$DENO_BIN" test tests-deno);                    R_TEST_DENO="$(awk "BEGIN{printf \"%.2f s\", $ms/1000}")"

  note "jest $R_TEST_JEST | bun $R_TEST_BUN | node --test $R_TEST_NODE | deno $R_TEST_DENO"
  cd - >/dev/null
fi

# ---------- stage 6: idle memory ----------
if stage_gate "Stage 6/6: idle memory (RSS of each plain HTTP server)"; then
  for rt in node bun deno; do
    case "$rt" in
      node) start_server "$NODE_BIN" server-node.js; port=3001 ;;
      bun)  start_server "$BUN_BIN"  server-bun.js;  port=3002 ;;
      deno) start_server "$DENO_BIN" run --allow-net server-deno.js; port=3003 ;;
    esac
    wait_port "$port"
    curl -s "http://localhost:$port/" >/dev/null
    sleep 1
    kb=$(awk '/VmRSS/ {print $2}' "/proc/$SERVER_PID/status")
    mb=$(( kb / 1024 ))
    note "$rt: $mb MB"
    case "$rt" in
      node) R_RSS_NODE="$mb MB" ;;
      bun)  R_RSS_BUN="$mb MB" ;;
      deno) R_RSS_DENO="$mb MB" ;;
    esac
    stop_server
  done
fi

# ---------- summary ----------
banner "Results"
printf '%-42s %-16s %-16s %-16s\n' "Benchmark" "Bun" "Deno" "Node.js"
printf '%-42s %-16s %-16s %-16s\n' "------------------------------------------" "----------------" "----------------" "----------------"
printf '%-42s %-16s %-16s %-16s\n' "HTTP throughput (req/s, single core)" "$R_THRU_BUN" "$R_THRU_DENO" "$R_THRU_NODE"
printf '%-42s %-16s %-16s %-16s\n' "Cold start (median)" "$R_COLD_BUN" "$R_COLD_DENO" "$R_COLD_NODE"
printf '%-42s %-16s %-16s %-16s\n' "Install cold cache" "$R_INST_BUN_COLD" "$R_INST_DENO_COLD" "$R_INST_NPM_COLD (npm)"
printf '%-42s %-16s %-16s %-16s\n' "Install warm cache" "$R_INST_BUN_WARM" "$R_INST_DENO_WARM" "$R_INST_NPM_WARM (npm)"
printf '%-42s %-16s %-16s %-16s\n' "200 tests / 20 files" "$R_TEST_BUN" "$R_TEST_DENO" "$R_TEST_NODE"
printf '%-42s %-16s\n' "  (Jest on Node, same suite)" "$R_TEST_JEST"
printf '%-42s %-16s %-16s %-16s\n' "Idle memory (RSS)" "$R_RSS_BUN" "$R_RSS_DENO" "$R_RSS_NODE"
echo
echo "JSON (3.3 MB): node: $R_JSON_NODE"
echo "               bun:  $R_JSON_BUN"
echo "               deno: $R_JSON_DENO"
echo
echo "Saturation check: $R_SAT"
echo
echo "Results are discussed in the blog post:"
echo "https://botmonster.com/web-dev/bun-vs-deno-vs-nodejs-javascript-runtime-2026/"
