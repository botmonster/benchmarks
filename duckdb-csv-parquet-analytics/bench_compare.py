#!/usr/bin/env python3
"""DuckDB vs Pandas vs Polars on the same filter / group-by / join.

Data is loaded once into each engine's native structure, then each operation is
timed in isolation (median of N repeats after a warmup). This isolates engine
compute from file I/O, matching how published DataFrame benchmarks measure.

Usage: bench_compare.py "<parquet-glob>" <zones.csv> <reps> [json-out]
"""

import glob
import json
import statistics
import sys
import time

import duckdb
import pandas as pd
import polars as pl

PARQUET_GLOB = sys.argv[1]
ZONES_CSV = sys.argv[2]
REPS = int(sys.argv[3]) if len(sys.argv) > 3 else 5
JSON_OUT = sys.argv[4] if len(sys.argv) > 4 else None

FILES = sorted(glob.glob(PARQUET_GLOB))
if not FILES:
    sys.exit(f"no parquet files matched {PARQUET_GLOB}")
COLS = ["trip_distance", "fare_amount", "tip_amount", "payment_type", "PULocationID"]


def timed(fn):
    """Median wall time over REPS runs, after one warmup. Returns (median_s, result)."""
    result = fn()
    samples = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples), result


def load():
    """Load the same rows into pandas, polars, and an in-memory DuckDB table."""
    pdf = pd.concat(
        [pd.read_parquet(f, columns=COLS) for f in FILES], ignore_index=True
    )
    zpd = pd.read_csv(ZONES_CSV)

    ldf = pl.from_pandas(pdf).with_columns(pl.col("PULocationID").cast(pl.Int64))
    zpl = pl.from_pandas(zpd).with_columns(pl.col("LocationID").cast(pl.Int64))

    con = duckdb.connect()
    con.execute(
        f"CREATE TABLE trips AS SELECT {', '.join(COLS)} FROM read_parquet($files)",
        {"files": FILES},
    )
    con.execute(
        "CREATE TABLE zones AS SELECT * FROM read_csv_auto($f)", {"f": ZONES_CSV}
    )
    return pdf, zpd, ldf, zpl, con


def main():
    print(f"Files: {len(FILES)} parquet, reps={REPS}")
    pdf, zpd, ldf, zpl, con = load()
    nrows = len(pdf)
    print(f"Rows loaded: {nrows:,}\n")

    # --- operation definitions per engine ---
    ops = {
        "filter": {
            "pandas": lambda: int(
                ((pdf.trip_distance > 5) & (pdf.fare_amount > 20)).sum()
            ),
            "polars": lambda: (
                ldf.filter(
                    (pl.col("trip_distance") > 5) & (pl.col("fare_amount") > 20)
                ).height
            ),
            "duckdb": lambda: con.execute(
                "SELECT count(*) FROM trips WHERE trip_distance > 5 AND fare_amount > 20"
            ).fetchall(),
        },
        "groupby": {
            "pandas": lambda: (
                pdf.groupby("PULocationID")
                .agg(
                    n=("fare_amount", "size"),
                    avg_fare=("fare_amount", "mean"),
                    avg_tip=("tip_amount", "mean"),
                )
                .reset_index()
                .shape
            ),
            "polars": lambda: (
                ldf.group_by("PULocationID")
                .agg(
                    pl.len(), pl.col("fare_amount").mean(), pl.col("tip_amount").mean()
                )
                .shape
            ),
            "duckdb": lambda: con.execute(
                "SELECT PULocationID, count(*), avg(fare_amount), avg(tip_amount) "
                "FROM trips GROUP BY PULocationID"
            ).fetchall(),
        },
        "join": {
            "pandas": lambda: (
                pdf.merge(zpd, left_on="PULocationID", right_on="LocationID")
                .groupby("Borough")
                .agg(n=("fare_amount", "size"), avg_fare=("fare_amount", "mean"))
                .reset_index()
                .shape
            ),
            "polars": lambda: (
                ldf.join(zpl, left_on="PULocationID", right_on="LocationID")
                .group_by("Borough")
                .agg(pl.len(), pl.col("fare_amount").mean())
                .shape
            ),
            "duckdb": lambda: con.execute(
                "SELECT z.Borough, count(*), avg(t.fare_amount) FROM trips t "
                "JOIN zones z ON t.PULocationID = z.LocationID GROUP BY z.Borough"
            ).fetchall(),
        },
    }

    engines = ["pandas", "duckdb", "polars"]
    table = {}
    for op, impls in ops.items():
        table[op] = {}
        for eng in engines:
            secs, _ = timed(impls[eng])
            table[op][eng] = secs
            print(f"{op:>8} | {eng:>7}: {secs * 1000:8.1f} ms")
        print()

    # --- summary table ---
    print(f"{'operation':>10} | {'pandas':>10} | {'duckdb':>10} | {'polars':>10}")
    print("-" * 52)
    for op in ops:
        r = table[op]
        print(
            f"{op:>10} | {r['pandas'] * 1000:8.0f}ms | {r['duckdb'] * 1000:8.0f}ms | {r['polars'] * 1000:8.0f}ms"
        )

    if JSON_OUT:
        with open(JSON_OUT, "w") as fh:
            json.dump(
                {
                    "rows": nrows,
                    "files": len(FILES),
                    "reps": REPS,
                    "duckdb_version": duckdb.__version__,
                    "pandas_version": pd.__version__,
                    "polars_version": pl.__version__,
                    "results_ms": {
                        op: {e: round(v * 1000, 1) for e, v in r.items()}
                        for op, r in table.items()
                    },
                },
                fh,
                indent=2,
            )
        print(f"\nwrote {JSON_OUT}")


if __name__ == "__main__":
    main()
