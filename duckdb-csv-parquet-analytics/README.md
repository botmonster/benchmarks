# DuckDB on CSV / Parquet: analytics with no server

Reproducible benchmarks behind [DuckDB is absurdly good at crunching gigabytes with no database server](https://botmonster.com/coding/duckdb-developers-analyze-csv-parquet-no-server/).

Everything installs into a local `./.tools` (a pinned DuckDB CLI plus a `uv` venv with pandas/polars/duckdb) and data lands in `./data`. No sudo, no system changes.

## What is tested

The dataset is the public [NYC TLC yellow taxi trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) (Parquet, one file per month) plus the taxi-zone lookup CSV. `--full` uses all 12 months of 2024 (~40M rows); the default uses 3 months (~10M rows).

Four stages, each mapping to a claim in the post:

1. **Direct query, no import** — point the DuckDB CLI at a Parquet glob and aggregate, with zero `CREATE TABLE`.
2. **DuckDB vs Pandas vs Polars** — filter, group-by, and join, each loaded once into the engine's native structure then timed in isolation (median of 5 runs after a warmup). This isolates engine compute from file I/O, the way published DataFrame benchmarks measure.
3. **CSV vs Parquet scan** — the same selective query run against a Parquet file and a CSV copy of the identical data, to show Parquet's projection/predicate pushdown.
4. **Out-of-core** — a large group-by + sort under `SET memory_limit='2GB'`, which forces DuckDB to spill intermediates to disk yet still complete.

## Replicating

On Ubuntu (x86_64), with [`uv`](https://docs.astral.sh/uv/) installed:

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/duckdb-csv-parquet-analytics
./run.sh              # 3 months (~10M rows), interactive stage gates
./run.sh --yes        # no prompts
./run.sh --yes --full # all of 2024 (~40M rows)
./run.sh --latest     # newest DuckDB + newest pandas/polars, unpinned
```

Pinned versions: DuckDB 1.5.4, pandas 2.2.3, polars 1.17.1, pyarrow 18.1.0. Data files are stable historical months, so downloads are deterministic; re-runs skip files already present in `./data`.

Files: [`run.sh`](run.sh) orchestrates; [`bench_compare.py`](bench_compare.py) is the three-engine comparison; [`bench_scan.py`](bench_scan.py) is CSV vs Parquet; [`bench_outofcore.py`](bench_outofcore.py) is the memory-limited aggregation; [`make_charts.py`](make_charts.py) renders exact SVG charts of the results from `results/compare.json`.

## Author's results

Machine: AMD Ryzen 9 5900X (12C/24T), 62 GB RAM, NVMe SSD, Ubuntu x86_64. Full 2024 dataset, 41,169,720 rows. Full detail in [`results/2026-07-09-author.md`](results/2026-07-09-author.md).

**Stage 2 — filter / group-by / join (median of 5):**

| operation | pandas | duckdb | polars |
|-----------|-------:|-------:|-------:|
| filter    | 127 ms |  23 ms | 157 ms |
| group-by  | 893 ms |  20 ms | 272 ms |
| join      | 6795 ms | 20 ms | 1316 ms |

On 24 threads DuckDB is fastest on all three: ~45x faster than pandas on group-by, ~340x on the join.

- **Stage 1:** direct `count`/`avg` over the Parquet glob, 41.2M rows, **0.06s**, no `CREATE TABLE`.
- **Stage 3:** same selective query, **Parquet 10.7 ms vs CSV 149.5 ms (14x)**.
- **Stage 4:** full sort of 41.2M rows under a 2GB `memory_limit` completes in **6.04s**, spilling **8.8 GB** to disk.

Absolute numbers are hardware-dependent; treat them as relative. What holds across machines is the ordering and the size of the gaps.

## License

[MIT](../LICENSE)
