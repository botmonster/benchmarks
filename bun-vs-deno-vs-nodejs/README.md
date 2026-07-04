# Bun vs Deno vs Node.js: runtime benchmarks

Companion benchmarks for the blog post
**[Bun vs Deno vs Node.js: which JavaScript runtime actually wins in 2026?](https://botmonster.com/web-dev/bun-vs-deno-vs-nodejs-javascript-runtime-2026/)**
The results, the analysis, and the story of how the first measurement attempt went wrong are discussed there; this folder holds the exact code that produced the numbers.

## What is tested

| Stage | What | How |
|---|---|---|
| 1 | HTTP throughput | Minimal JSON endpoint per runtime ([server-node.js](server-node.js), [server-bun.js](server-bun.js), [server-deno.js](server-deno.js)), per-request `JSON.stringify`, no framework. Server pinned to a single core, loaded with 200 keep-alive connections for 15 s, two passes, averaged. |
| 2 | Process cold start | 15 timed runs of [hello.js](hello.js) per runtime, median reported. |
| 3 | JSON parse/stringify | [json-bench.js](json-bench.js): 3.3 MB payload, 30-iteration averages after warmup. |
| 4 | Package install | [install-bench/package.json](install-bench/package.json) (~585 packages resolved) installed with bun, deno, and npm; cold cache then warm cache. Caches are isolated in a temp dir, your real npm/bun/deno caches are never touched. |
| 5 | Test runners | 200 trivial tests across 20 files, equivalent suites per dialect; Jest (baseline), `bun test`, `node --test`, `deno test`. |
| 6 | Idle memory | RSS of each plain HTTP server after one request. |

## Methodology notes

- The load generator is [oha](https://github.com/hatoo/oha), written in Rust. A JavaScript load generator (autocannon) saturated before the fast runtimes did and clamped Bun and Deno to identical numbers; the post's "The mistake I made first" section covers this. The script reproduces that lesson as a sanity check: after measuring, it points two parallel clients at the same server and warns you if the combined throughput exceeds the single-client result by more than 15%.
- The server is pinned to core 0 with `taskset`; the client gets every core except core 0 and its SMT sibling, so they never compete for the same physical core.
- `node --test` is invoked with explicit file globs. A bare directory argument silently runs zero tests and reports success in a fraction of a second, which looks like a spectacular benchmark win until you read the test counts.
- Deno's install links packages from a global cache instead of materializing the full `node_modules` tree, so its install numbers do less disk work than npm's or bun's.

## Replicate it

On Ubuntu 22.04+ (x86_64):

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/bun-vs-deno-vs-nodejs
./run.sh
```

The script installs pinned runtime versions (Node 24.18.0, Bun 1.3.14, Deno 2.9.1) plus oha into a local `.tools/` directory. No sudo, no system changes; delete `.tools/` afterwards and it is gone. It walks you through the six stages (each can be skipped) and prints a summary table at the end.

Flags:

- `--yes` run all stages without prompting
- `--latest` benchmark the newest Node LTS / Bun / Deno instead of the pinned versions

Prerequisites (usually already present): `curl unzip xz-utils util-linux python3 iproute2`. Install with:

```bash
sudo apt-get install -y curl unzip xz-utils util-linux python3 iproute2
```

4+ CPU cores are recommended; with fewer, the script runs unpinned and warns that throughput numbers may be client-bound.

## Author's results

<!-- RESULTS:START -->
Run on 2026-07-04, raw output in [results/2026-07-04-author.md](results/2026-07-04-author.md):

| Benchmark | Bun 1.3.14 | Deno 2.9.1 | Node.js 24.18.0 |
|---|---|---|---|
| HTTP throughput (req/s, single core) | 122,170 | **133,093** | 47,734 |
| Cold start (median of 15) | **11 ms** | 14 ms | 21 ms |
| Install, cold cache (585 packages) | **5.8 s** | 6.0 s | 11.8 s (npm) |
| Install, warm cache | 0.17 s | **0.12 s** | 2.0 s (npm) |
| 200 tests / 20 files | **0.02 s** | 1.04 s | 0.14 s (`node --test`), 0.81 s (Jest) |
| `JSON.parse`, 3.3 MB | **11.9 ms** | 12.1 ms | 14.3 ms |
| `JSON.stringify`, 3.3 MB | **5.5 ms** | 6.5 ms | 13.6 ms |
| Idle memory (RSS) | **36 MB** | 51 MB | 49 MB |

The saturation check passed (+1.9% with two parallel clients), so these are server-bound numbers. Deno 2.7.4 measured 102,950 req/s on the same machine the same day; 2.9.1 gained ~30% and took the throughput lead from Bun.
<!-- RESULTS:END -->

Machine: 12-core / 24-thread x86_64 Linux desktop, kernel 6.17, `powersave` CPU governor. The absolute numbers are hardware-dependent; the ratios between runtimes are what the post discusses.
