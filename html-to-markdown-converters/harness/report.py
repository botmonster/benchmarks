#!/usr/bin/env python3
"""Stage 5: turn scores.csv and timings.json into the league table and the feature grid.

Usage: report.py [--results DIR] [--corpus DIR]

Writes results/report.md and results/charts/*.svg. Ranking is by weighted probe
pass rate, ties broken on text retention, then on median milliseconds per page.
"""

import argparse
import csv
import json
import os
from collections import defaultdict

FEATURE_ORDER = [
    "headings", "tables", "code", "lists", "links", "images",
    "inline", "escaping", "footnotes", "math", "entities",
    "structure", "boilerplate",
]

PALETTE = ["#2f6f9f", "#c2632b", "#3f8a58", "#8a4f9e", "#b03a48", "#7a6a3a",
           "#4a7fb5", "#d08a3e", "#5aa06f", "#9a6bb0", "#c2545f"]


def pct(x):
    return "-" if x is None else f"{100 * x:.0f}%"


def load(results):
    with open(os.path.join(results, "scores.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("probe_pass_rate", "retention", "boilerplate_leakage"):
            r[k] = float(r[k]) if r[k] not in ("", "None") else None
        for k in ("probes_passed", "probes_total", "output_bytes"):
            r[k] = int(r[k])
        r["ranked"] = r["ranked"] == "True"
    with open(os.path.join(results, "timings.json")) as fh:
        timings = json.load(fh)
    with open(os.path.join(results, "probe-results.json")) as fh:
        detail = json.load(fh)
    return rows, timings, detail


def aggregate(rows, timings, detail):
    tools = defaultdict(lambda: {
        "passed": 0, "total": 0, "retention": [], "leakage": [],
        "ms": [], "bytes": 0, "features": defaultdict(lambda: [0, 0]),
    })
    for r in rows:
        t = tools[r["tool"]]
        t["lang"] = r["lang"]
        t["kind"] = r["kind"]
        t["ranked"] = r["ranked"]
        t["passed"] += r["probes_passed"]
        t["total"] += r["probes_total"]
        if r["retention"] is not None:
            t["retention"].append(r["retention"])
        if r["boilerplate_leakage"] is not None:
            t["leakage"].append(r["boilerplate_leakage"])
        t["bytes"] += r["output_bytes"]
        ms = timings["pages"][r["page"]]["tools"][r["tool"]]["median_ms"]
        if ms is not None:
            t["ms"].append(ms)
        for feature, (ok, tot) in detail[r["page"]][r["tool"]]["per_feature"].items():
            bucket = t["features"][feature]
            bucket[0] += ok
            bucket[1] += tot

    out = {}
    for name, t in tools.items():
        out[name] = {
            "lang": t["lang"],
            "kind": t["kind"],
            "ranked": t["ranked"],
            "version": timings["tools"][name]["version"],
            "repo": timings["tools"][name]["repo"],
            "notes": timings["tools"][name]["notes"],
            "pass_rate": t["passed"] / t["total"] if t["total"] else None,
            "passed": t["passed"],
            "total": t["total"],
            "retention": sum(t["retention"]) / len(t["retention"]) if t["retention"] else None,
            "leakage": sum(t["leakage"]) / len(t["leakage"]) if t["leakage"] else None,
            "total_ms": sum(t["ms"]),
            "median_ms": sorted(t["ms"])[len(t["ms"]) // 2] if t["ms"] else None,
            "bytes": t["bytes"],
            "features": {f: tuple(v) for f, v in t["features"].items()},
        }
    return out


def rank(agg):
    ranked = [(n, a) for n, a in agg.items() if a["ranked"]]
    ranked.sort(key=lambda kv: (-(kv[1]["pass_rate"] or 0), -(kv[1]["retention"] or 0), kv[1]["total_ms"]))
    return ranked


def bar_chart(path, title, labels, values, fmt="{:.0f}%", scale=100):
    row_h, pad_l, pad_t, width = 26, 210, 46, 760
    height = pad_t + row_h * len(labels) + 16
    top = max(values) * scale if values else 1
    top = max(top, 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="system-ui, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="16" y="26" font-size="15" font-weight="600" fill="#1a1a1a">{title}</text>',
    ]
    span = width - pad_l - 90
    for i, (label, value) in enumerate(zip(labels, values)):
        y = pad_t + i * row_h
        w = max(1, (value * scale / top) * span)
        parts.append(f'<text x="{pad_l - 10}" y="{y + 14}" font-size="12" text-anchor="end" fill="#333">{label}</text>')
        parts.append(f'<rect x="{pad_l}" y="{y + 3}" width="{w:.1f}" height="16" rx="3" fill="{PALETTE[i % len(PALETTE)]}"/>')
        parts.append(f'<text x="{pad_l + w + 8:.1f}" y="{y + 16}" font-size="12" fill="#444">{fmt.format(value * scale)}</text>')
    parts.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(parts) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="/bench/results")
    ap.add_argument("--corpus", default="/bench/corpus")
    args = ap.parse_args()

    rows, timings, detail = load(args.results)
    agg = aggregate(rows, timings, detail)
    ranked = rank(agg)
    pages = sorted({r["page"] for r in rows})

    charts = os.path.join(args.results, "charts")
    os.makedirs(charts, exist_ok=True)
    bar_chart(os.path.join(charts, "pass-rate.svg"), "Probe pass rate across 10 pages",
              [n for n, _ in ranked], [a["pass_rate"] for _, a in ranked])
    bar_chart(os.path.join(charts, "retention.svg"), "Article text retention",
              [n for n, _ in ranked], [a["retention"] for _, a in ranked])
    by_speed = sorted(ranked, key=lambda kv: kv[1]["total_ms"])
    bar_chart(os.path.join(charts, "speed.svg"), "Total time to convert all 10 pages (ms, lower is better)",
              [n for n, _ in by_speed], [a["total_ms"] for _, a in by_speed], fmt="{:.0f}", scale=1)

    lines = []
    w = lines.append
    w("# HTML to Markdown benchmark results\n")
    w(f"Corpus: {len(pages)} open-license pages. Probes: {sum(a['total'] for _, a in ranked[:1])} per tool "
      f"(some probes apply only to converters or only to extractors).")
    w(f"Repetitions per conversion: {timings['reps']}. Subprocess spawn overhead on this machine: "
      f"{timings['spawn_overhead_ms']} ms, which is included in the pandoc, Go and Rust timings.\n")

    w("## League table\n")
    w("| # | Tool | Lang | Kind | Probe pass | Retention | Boilerplate | Total ms | Output |")
    w("|---|---|---|---|---|---|---|---|---|")
    for i, (name, a) in enumerate(ranked, 1):
        w(f"| {i} | [{name}]({a['repo']}) | {a['lang']} | {a['kind']} | {pct(a['pass_rate'])} "
          f"({a['passed']}/{a['total']}) | {pct(a['retention'])} | {pct(a['leakage'])} | "
          f"{a['total_ms']:.0f} | {a['bytes'] // 1024} KB |")
    w("")
    w("Boilerplate is the share of nav, header and footer wording that reached the output. "
      "High is expected for a converter and bad for an extractor.\n")

    unranked = [(n, a) for n, a in agg.items() if not a["ranked"]]
    if unranked:
        w("### Scored but not ranked\n")
        w("| Tool | Probe pass | Retention | Total ms | Why |")
        w("|---|---|---|---|---|")
        for name, a in unranked:
            w(f"| {name} | {pct(a['pass_rate'])} ({a['passed']}/{a['total']}) | {pct(a['retention'])} | "
              f"{a['total_ms']:.0f} | {a['notes']} |")
        w("")

    w("## Pass rate by HTML feature\n")
    features = [f for f in FEATURE_ORDER if any(f in a["features"] for _, a in ranked)]
    w("| Tool | " + " | ".join(features) + " |")
    w("|---" * (len(features) + 1) + "|")
    for name, a in ranked:
        cells = []
        for f in features:
            ok, tot = a["features"].get(f, (0, 0))
            cells.append(f"{100 * ok / tot:.0f}%" if tot else "-")
        w(f"| {name} | " + " | ".join(cells) + " |")
    w("")

    w("## Per page\n")
    for page in pages:
        w(f"### {page}\n")
        w("| Tool | Probe pass | Retention | Boilerplate | Median ms |")
        w("|---|---|---|---|---|")
        for name, _ in ranked:
            r = next((x for x in rows if x["page"] == page and x["tool"] == name), None)
            if not r:
                continue
            ms = timings["pages"][page]["tools"][name]["median_ms"]
            w(f"| {name} | {pct(r['probe_pass_rate'])} | {pct(r['retention'])} | "
              f"{pct(r['boilerplate_leakage'])} | {ms:.1f} |")
        w("")

    w("## Probes nothing passed\n")
    universal = []
    for page in pages:
        ids = {}
        for name, _ in ranked:
            for pid, ok in detail[page][name]["probes"].items():
                ids.setdefault(pid, []).append(ok)
        for pid, results in ids.items():
            if not any(results):
                universal.append((page, pid))
    if universal:
        for page, pid in universal:
            w(f"- `{page}` / `{pid}`")
    else:
        w("None. Every probe is passed by at least one tool.")
    w("")

    path = os.path.join(args.results, "report.md")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path} and {charts}/*.svg")

    print("\nLeague table:")
    for i, (name, a) in enumerate(ranked, 1):
        print(f"{i:2}. {name:<26} {pct(a['pass_rate']):>5}  ret {pct(a['retention']):>5}  "
              f"boiler {pct(a['leakage']):>5}  {a['total_ms']:7.0f} ms")


if __name__ == "__main__":
    main()
