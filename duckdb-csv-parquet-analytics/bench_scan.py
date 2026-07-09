#!/usr/bin/env python3
"""CSV vs Parquet: same selective query, measured on each format.

Shows Parquet's projection + predicate pushdown against a plain CSV scan of the
identical data. Usage: bench_scan.py <file.parquet> <file.csv> <reps>
"""

import statistics
import sys
import time

import duckdb

PARQUET = sys.argv[1]
CSV = sys.argv[2]
REPS = int(sys.argv[3]) if len(sys.argv) > 3 else 5

QUERY = (
    "SELECT PULocationID, count(*), avg(fare_amount) "
    "FROM read_{reader}($f) WHERE fare_amount > 20 GROUP BY PULocationID"
)


def timed(reader, path):
    con = duckdb.connect()
    q = QUERY.format(reader=reader)
    con.execute(q, {"f": path}).fetchall()  # warmup
    samples = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        con.execute(q, {"f": path}).fetchall()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples)


def main():
    pq = timed("parquet", PARQUET)
    csv = timed("csv_auto", CSV)
    print(f"parquet scan: {pq * 1000:8.1f} ms")
    print(f"csv scan:     {csv * 1000:8.1f} ms")
    print(f"parquet is {csv / pq:.1f}x faster on this selective query")


if __name__ == "__main__":
    main()
