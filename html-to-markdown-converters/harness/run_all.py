#!/usr/bin/env python3
"""Stage 3: convert every fixture with every tool and time each conversion.

Usage: run_all.py [--reps N] [--corpus DIR] [--out DIR] [--only TOOL,TOOL]

Writes results/outputs/<page>/<tool>.md, results/timings.json and
results/versions.txt. Timing is the median of N repetitions after one warmup.
CLI tools are subprocesses, so their numbers include process start; the
spawn_overhead_ms field records how much that is.
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import ALL  # noqa: E402

SAFE = str.maketrans({"/": "-", " ": "-", "(": "", ")": ""})


def slugify(name):
    return name.translate(SAFE).lower()


def load_corpus(corpus_dir):
    pages = []
    root = os.path.join(corpus_dir, "pages")
    for slug in sorted(os.listdir(root)):
        page_dir = os.path.join(root, slug)
        html_path = os.path.join(page_dir, "page.html")
        if not os.path.isfile(html_path):
            continue
        with open(os.path.join(page_dir, "meta.json")) as fh:
            meta = json.load(fh)
        with open(html_path, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        pages.append({"slug": slug, "meta": meta, "html": html})
    return pages


def measure_spawn_overhead(reps=10):
    """How long an empty subprocess round trip costs, so CLI timings can be read honestly."""
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        subprocess.run(["true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        samples.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(samples), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=7)
    ap.add_argument("--corpus", default="/bench/corpus")
    ap.add_argument("--out", default="/bench/results")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    adapters = ALL
    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        adapters = [a for a in ALL if a.name in wanted]

    pages = load_corpus(args.corpus)
    print(f"corpus: {len(pages)} pages, tools: {len(adapters)}, reps: {args.reps}", flush=True)

    out_root = os.path.join(args.out, "outputs")
    os.makedirs(out_root, exist_ok=True)

    versions = {}
    for adapter in adapters:
        versions[adapter.name] = adapter.version()
    with open(os.path.join(args.out, "versions.txt"), "w") as fh:
        for adapter in adapters:
            fh.write(f"{adapter.name}\t{adapter.lang}\t{adapter.kind}\t{versions[adapter.name]}\n")
    print("versions:", json.dumps(versions, indent=2), flush=True)

    timings = {
        "reps": args.reps,
        "spawn_overhead_ms": measure_spawn_overhead(),
        "tools": {a.name: {"lang": a.lang, "kind": a.kind, "repo": a.repo,
                           "version": versions[a.name], "ranked": a.ranked,
                           "notes": a.notes} for a in adapters},
        "pages": {},
    }

    for page in pages:
        slug = page["slug"]
        base_url = page["meta"]["source_url"]
        page_out = os.path.join(out_root, slug)
        os.makedirs(page_out, exist_ok=True)
        timings["pages"][slug] = {"bytes": len(page["html"].encode("utf-8")), "tools": {}}
        print(f"\n{slug} ({len(page['html']) // 1024} KB)", flush=True)

        for adapter in adapters:
            samples = []
            markdown = ""
            error = None
            try:
                markdown = adapter.convert(page["html"], base_url)
                for _ in range(args.reps):
                    t0 = time.perf_counter()
                    markdown = adapter.convert(page["html"], base_url)
                    samples.append((time.perf_counter() - t0) * 1000)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

            path = os.path.join(page_out, f"{slugify(adapter.name)}.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(markdown or "")

            record = {
                "median_ms": round(statistics.median(samples), 3) if samples else None,
                "min_ms": round(min(samples), 3) if samples else None,
                "output_bytes": len((markdown or "").encode("utf-8")),
                "error": error,
            }
            timings["pages"][slug]["tools"][adapter.name] = record
            status = "FAIL" if error else f"{record['median_ms']:8.1f} ms  {record['output_bytes']:>8} B"
            print(f"  {adapter.name:<26} {status}", flush=True)
            if error:
                print(f"      {error[:200]}", flush=True)

    with open(os.path.join(args.out, "timings.json"), "w") as fh:
        json.dump(timings, fh, indent=2)
        fh.write("\n")
    print(f"\nwrote {os.path.join(args.out, 'timings.json')}", flush=True)


if __name__ == "__main__":
    main()
