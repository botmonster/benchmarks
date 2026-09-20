#!/usr/bin/env python3
"""Stage 2: check the ten fixtures are intact and print every tool's version.

Usage: verify_corpus.py [--corpus DIR] [--results DIR]
"""

import argparse
import csv
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import ALL  # noqa: E402
from probes import PROBE_TYPES  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="/bench/corpus")
    ap.add_argument("--results", default="/bench/results")
    args = ap.parse_args()

    with open(os.path.join(args.corpus, "sources.tsv")) as fh:
        sources = [row for row in csv.reader(fh, delimiter="\t") if row and row[0]]

    problems = []
    total_probes = 0
    print(f"{'fixture':<34} {'bytes':>9}  {'probes':>6}  license")
    for row in sources:
        slug = row[0]
        page_dir = os.path.join(args.corpus, "pages", slug)
        html = os.path.join(page_dir, "page.html")
        meta = os.path.join(page_dir, "meta.json")
        probes = os.path.join(page_dir, "probes.yaml")
        if not os.path.isfile(html):
            problems.append(f"{slug}: page.html missing")
            continue
        size = os.path.getsize(html)
        if size < 10_000:
            problems.append(f"{slug}: page.html is only {size} bytes")
        try:
            with open(meta) as fh:
                info = json.load(fh)
        except Exception as exc:
            problems.append(f"{slug}: meta.json unreadable ({exc})")
            continue
        try:
            with open(probes) as fh:
                spec = yaml.safe_load(fh) or {}
            plist = spec.get("probes", [])
        except Exception as exc:
            problems.append(f"{slug}: probes.yaml unreadable ({exc})")
            plist = []
        ids = set()
        for probe in plist:
            if probe["type"] not in PROBE_TYPES:
                problems.append(f"{slug}/{probe['id']}: unknown probe type {probe['type']}")
            if probe["id"] in ids:
                problems.append(f"{slug}: duplicate probe id {probe['id']}")
            ids.add(probe["id"])
        total_probes += len(plist)
        print(f"{slug:<34} {size:>9}  {len(plist):>6}  {info['license']}")

    print(f"\n{len(sources)} fixtures, {total_probes} probes total")

    print("\nTool versions inside this image:")
    os.makedirs(args.results, exist_ok=True)
    with open(os.path.join(args.results, "versions.txt"), "w") as fh:
        for adapter in ALL:
            version = adapter.version()
            flag = "" if adapter.ranked else "   (not ranked)"
            print(f"  {adapter.name:<26} {adapter.lang:<11} {adapter.kind:<10} {version}{flag}")
            fh.write(f"{adapter.name}\t{adapter.lang}\t{adapter.kind}\t{version}\n")
            if version.startswith("unknown"):
                problems.append(f"{adapter.name}: version could not be read")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("\nCorpus and toolchain verified.")


if __name__ == "__main__":
    main()
