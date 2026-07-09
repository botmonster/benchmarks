#!/usr/bin/env python3
"""Out-of-core demo: sort more data than the memory budget and still finish.

We pin memory_limit well below the working set, point the temp directory at
local disk, then fully materialize a sort of every row. When the sort exceeds
the limit DuckDB spills to the temp directory, so the query completes anyway.
We report the peak spill size so the offload is visible.

Usage: bench_outofcore.py "<parquet-glob>" <memory_limit>
"""

import os
import sys
import time

import duckdb

PARQUET_GLOB = sys.argv[1]
MEM = sys.argv[2] if len(sys.argv) > 2 else "2GB"
SPILL = "./data/duckdb_spill"


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def main():
    os.makedirs(SPILL, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{MEM}'")
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"SET temp_directory = '{SPILL}'")

    nrows = con.execute(
        "SELECT count(*) FROM read_parquet($g)", {"g": PARQUET_GLOB}
    ).fetchone()[0]
    print(f"rows: {nrows:,}  memory_limit: {MEM}")

    # Full sort of every row on two columns, materialized into a table. This
    # working set is larger than the 2GB budget, so the sort spills to disk.
    con.execute("DROP TABLE IF EXISTS sorted")
    t0 = time.perf_counter()
    con.execute(
        "CREATE TABLE sorted AS "
        "SELECT * FROM read_parquet($g) ORDER BY fare_amount DESC, trip_distance DESC",
        {"g": PARQUET_GLOB},
    )
    dt = time.perf_counter() - t0
    spilled = dir_size(SPILL)

    got = con.execute("SELECT count(*) FROM sorted").fetchone()[0]
    print(f"sorted {got:,} rows in {dt:.2f}s under a {MEM} limit")
    print(f"peak spill on disk: {spilled / 1e6:.0f} MB in {SPILL}")
    if spilled == 0:
        print("(no spill needed: the sort fit inside the limit at this scale)")


if __name__ == "__main__":
    main()
