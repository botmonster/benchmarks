#!/usr/bin/env python3
"""Emit two editorial-style SVG charts from the measured benchmark numbers.

Reads results/compare.json (the three-engine numbers) and writes two SVGs to the
output directory. Palette matches the post's hero image (deep teal / warm amber /
crisp white) and is CVD-validated. Bars are labelled with exact values so the
visual can't misread the data.

Usage: make_charts.py <output-dir>
"""

import json
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "results", "compare.json")) as fh:
    DATA = json.load(fh)
MS = DATA["results_ms"]

# CSV-vs-Parquet scan numbers from results/2026-07-09-author.md (bench_scan.py).
PARQUET_MS = 10.7
CSV_MS = 149.5

# Palette (validated: amber vs teal CVD dE 71, contrast/chroma pass on light card)
AMBER = "#c9760f"  # DuckDB, the fast one
TEAL = "#0a9aa8"  # Polars
GRAY = "#9aa0a3"  # Pandas baseline
INK = "#2b2b2b"
MUTED = "#6b7378"
CARD = "#fbfaf7"
GRID = "#e6e4de"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def fmt_ms(v):
    return f"{v / 1000:.1f}s" if v >= 1000 else f"{round(v)}ms"


def fmt_x(v):
    return f"{v:.0f}×" if v >= 10 else f"{v:.1f}×"


# ---------------------------------------------------------------- chart 1
def speedup_chart():
    ops = [("Filter", "filter"), ("Group-by", "groupby"), ("Join", "join")]
    W, H = 760, 400
    plot_left, plot_right = 168, 626
    plot_w = plot_right - plot_left
    dmin, dmax = 0.7, 560.0
    span = math.log10(dmax) - math.log10(dmin)

    def X(v):
        return plot_left + plot_w * (math.log10(v) - math.log10(dmin)) / span

    base_x = X(1.0)
    s = []
    s.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">'
    )
    s.append(f'<rect width="{W}" height="{H}" rx="14" fill="{CARD}"/>')
    s.append(
        f'<text x="36" y="42" font-size="22" font-weight="700" fill="{INK}">'
        f"How much faster than Pandas?</text>"
    )
    s.append(
        f'<text x="36" y="66" font-size="13" fill="{MUTED}">'
        f"41M NYC taxi rows, median of 5 runs. Bars are relative to Pandas (1×); longer is faster. "
        f"Log scale.</text>"
    )

    # legend (top-right)
    lx = 512
    s.append(f'<rect x="{lx}" y="30" width="13" height="13" rx="3" fill="{AMBER}"/>')
    s.append(f'<text x="{lx + 19}" y="41" font-size="13" fill="{INK}">DuckDB</text>')
    s.append(
        f'<rect x="{lx + 92}" y="30" width="13" height="13" rx="3" fill="{TEAL}"/>'
    )
    s.append(f'<text x="{lx + 111}" y="41" font-size="13" fill="{INK}">Polars</text>')

    top, bot = 96, 316
    # gridlines + ticks
    for tick in (1, 10, 100):
        gx = X(tick)
        s.append(
            f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{bot}" stroke="{GRID}" stroke-width="1"/>'
        )
        s.append(
            f'<text x="{gx:.1f}" y="{bot + 18}" font-size="11" fill="{MUTED}" text-anchor="middle">{tick}×</text>'
        )
    # pandas baseline (1x) emphasised
    s.append(
        f'<line x1="{base_x:.1f}" y1="{top}" x2="{base_x:.1f}" y2="{bot}" stroke="{GRAY}" stroke-width="2"/>'
    )
    s.append(
        f'<text x="{base_x:.1f}" y="{top - 8}" font-size="11" fill="{MUTED}" text-anchor="middle">Pandas 1×</text>'
    )

    for i, (label, key) in enumerate(ops):
        gy = 108 + i * 74
        p = MS[key]["pandas"]
        s.append(
            f'<text x="36" y="{gy + 30}" font-size="16" font-weight="700" fill="{INK}">{label}</text>'
        )
        for j, (eng, color) in enumerate((("duckdb", AMBER), ("polars", TEAL))):
            v = MS[key][eng]
            sp = p / v
            by = gy + j * 30
            bx = X(sp)
            if sp >= 1:
                x0, w = base_x, bx - base_x
            else:  # slower than Pandas: bar extends left of the 1x line
                x0, w = bx, base_x - bx
            s.append(
                f'<rect x="{x0:.1f}" y="{by}" width="{max(w, 2):.1f}" height="22" rx="4" fill="{color}"/>'
            )
            end = x0 + w if sp >= 1 else x0
            anchor = "start" if sp >= 1 else "end"
            tx = end + 8 if sp >= 1 else end - 8
            s.append(
                f'<text x="{tx:.1f}" y="{by + 16}" font-size="15" font-weight="700" '
                f'fill="{color}" text-anchor="{anchor}">{fmt_x(sp)}</text>'
            )
            sx = tx + 42 if sp >= 1 else tx - 42
            s.append(
                f'<text x="{sx:.1f}" y="{by + 16}" font-size="11" '
                f'fill="{MUTED}" text-anchor="{anchor}">({fmt_ms(v)})</text>'
            )
    pf, gf, jf = MS["filter"]["pandas"], MS["groupby"]["pandas"], MS["join"]["pandas"]
    s.append(
        f'<text x="36" y="384" font-size="11" fill="{MUTED}">Pandas baseline: '
        f"{fmt_ms(pf)} filter · {fmt_ms(gf)} group-by · {fmt_ms(jf)} join. "
        f"Times in parentheses are each engine's median.</text>"
    )
    s.append("</svg>")
    return "\n".join(s)


# ---------------------------------------------------------------- chart 2
def scan_chart():
    W, H = 760, 240
    plot_left, plot_right = 150, 620
    plot_w = plot_right - plot_left
    vmax = CSV_MS * 1.05
    rows = [("Parquet", PARQUET_MS, AMBER), ("CSV", CSV_MS, GRAY)]
    s = []
    s.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">'
    )
    s.append(f'<rect width="{W}" height="{H}" rx="14" fill="{CARD}"/>')
    s.append(
        f'<text x="36" y="42" font-size="22" font-weight="700" fill="{INK}">Same query, two file formats</text>'
    )
    s.append(
        f'<text x="36" y="66" font-size="13" fill="{MUTED}">'
        f"One month of taxi data, selective GROUP BY. Column pruning and row-group skipping do the work.</text>"
    )
    for i, (label, v, color) in enumerate(rows):
        by = 104 + i * 54
        w = plot_w * v / vmax
        s.append(
            f'<text x="36" y="{by + 24}" font-size="16" font-weight="700" fill="{INK}">{label}</text>'
        )
        s.append(
            f'<rect x="{plot_left}" y="{by}" width="{max(w, 2):.1f}" height="34" rx="4" fill="{color}"/>'
        )
        s.append(
            f'<text x="{plot_left + w + 10:.1f}" y="{by + 23}" font-size="15" font-weight="700" fill="{color}">{v:.0f}ms</text>'
        )
    # big callout
    s.append(
        f'<text x="{plot_right - 6}" y="212" font-size="30" font-weight="800" fill="{AMBER}" text-anchor="end">14× faster</text>'
    )
    s.append(
        f'<text x="{plot_right - 6}" y="232" font-size="12" fill="{MUTED}" text-anchor="end">Parquet over CSV on the same data</text>'
    )
    s.append("</svg>")
    return "\n".join(s)


def main():
    os.makedirs(OUT, exist_ok=True)
    a = os.path.join(OUT, "benchmark-engine-speedup.svg")
    b = os.path.join(OUT, "benchmark-parquet-vs-csv.svg")
    with open(a, "w") as fh:
        fh.write(speedup_chart())
    with open(b, "w") as fh:
        fh.write(scan_chart())
    print("wrote", a)
    print("wrote", b)


if __name__ == "__main__":
    main()
