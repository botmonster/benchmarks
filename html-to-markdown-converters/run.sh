#!/usr/bin/env bash
# Reproduces the benchmarks behind:
# https://botmonster.com/coding/best-10-html-to-markdown-converters-in-2026/
# Builds one Docker image holding all ten converters (five Python libraries, two
# npm packages, pandoc, a Go binary and a Rust binary), then converts ten
# open-license web pages with each of them and scores the output. Nothing is
# installed on your machine; everything runs inside the container. Results land
# in ./results. See README.md for flags.
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

IMAGE="html2md-bench:pinned"
REPS=7

YES=0
LATEST=0
SKIP_BUILD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) YES=1 ;;
    --latest) LATEST=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --reps) shift; REPS="${1:?--reps needs a number}" ;;
    --reps=*) REPS="${1#*=}" ;;
    *) echo "usage: $0 [--yes] [--latest] [--skip-build] [--reps N]"; exit 1 ;;
  esac
  shift
done

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
missing=""
for c in docker python3; do
  command -v "$c" >/dev/null || missing="$missing $c"
done
if [ -n "$missing" ]; then
  echo "Missing tools:$missing"
  echo "Install Docker: https://docs.docker.com/engine/install/  and python3: sudo apt-get install -y python3"
  exit 1
fi
docker info >/dev/null 2>&1 || { echo "The Docker daemon is not reachable. Start it, or add yourself to the docker group."; exit 1; }
note "Docker: $(docker --version)"
note "CPUs: $(nproc)  RAM: $(free -g | awk '/^Mem:/{print $2}')GB"
[ -f corpus/sources.tsv ] || { echo "corpus/sources.tsv is missing, are you in the benchmark folder?"; exit 1; }

# ---------- stage 1: build ----------
if [ "$SKIP_BUILD" = 1 ]; then
  banner "Stage 1/5: Build the image (skipped)"
  docker image inspect "$IMAGE" >/dev/null 2>&1 || { echo "--skip-build was passed but $IMAGE does not exist yet."; exit 1; }
elif stage_gate "Stage 1/5: Build the image with all ten converters"; then
  if [ "$LATEST" = 1 ]; then
    note "Resolving the newest published version of every tool"
    python3 tools/resolve-latest.py > versions.latest.env
    cat versions.latest.env
    cp versions.latest.env versions.env
  fi
  note "Pinned versions:"
  sed 's/^/  /' versions.env
  ./build.sh "$IMAGE"
fi

DOCKER_RUN=(docker run --rm
  --user "$(id -u):$(id -g)"
  -e HOME=/tmp
  -v "$PWD/harness:/bench/harness:ro"
  -v "$PWD/corpus:/bench/corpus:ro"
  -v "$PWD/results:/bench/results"
  "$IMAGE")

mkdir -p results

# ---------- stage 2: verify the corpus ----------
if stage_gate "Stage 2/5: Verify the ten fixtures and print tool versions"; then
  "${DOCKER_RUN[@]}" /bench/harness/verify_corpus.py
fi

# ---------- stage 3: convert ----------
if stage_gate "Stage 3/5: Convert 10 pages with every tool, $REPS timed repetitions each"; then
  "${DOCKER_RUN[@]}" /bench/harness/run_all.py --reps "$REPS" | tee results/convert.log
fi

# ---------- stage 4: score ----------
if stage_gate "Stage 4/5: Score probes, text retention and boilerplate leakage"; then
  "${DOCKER_RUN[@]}" /bench/harness/score.py
fi

# ---------- stage 5: report ----------
if stage_gate "Stage 5/5: Build the league table, the feature grid and the charts"; then
  "${DOCKER_RUN[@]}" /bench/harness/report.py
fi

banner "Done"
note "League table and per-feature grid: results/report.md"
note "Raw Markdown from every tool:      results/outputs/<page>/<tool>.md"
note "Machine-readable scores:           results/scores.csv, results/timings.json"
note "Charts:                            results/charts/*.svg"
echo
echo "Post: https://botmonster.com/coding/best-10-html-to-markdown-converters-in-2026/"
