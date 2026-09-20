#!/usr/bin/env python3
"""Stage 4: score every output against its page's probes, plus two text measures.

Usage: score.py [--corpus DIR] [--results DIR]

Reads results/outputs/ and writes results/scores.csv and results/probe-results.json.

Three numbers per (page, tool):
  probe pass rate     share of that page's probes the output satisfies
  text retention      how much of the article's own words survived
  boilerplate leakage how much of the nav/header/footer wording came along

Retention and leakage are multiset recall over word tokens. Leakage counts only
boilerplate words that do not also occur in the article, so a converter is not
charged for the word "Markdown" appearing in a sidebar.
"""

import argparse
import copy
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter

import yaml
from lxml import html as lxml_html
from lxml.cssselect import CSSSelector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import ALL  # noqa: E402
from probes import FEATURES, applies, evaluate  # noqa: E402

SAFE = str.maketrans({"/": "-", " ": "-", "(": "", ")": ""})
TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)

MD_STRIP = [
    (re.compile(r"^\s{0,3}(#{1,6})\s+", re.M), ""),
    (re.compile(r"^\s{0,3}>\s?", re.M), ""),
    (re.compile(r"^\s*([-*+]|\d+[.)])\s+", re.M), ""),
    (re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", re.M), ""),
    (re.compile(r"`{1,3}"), " "),
    (re.compile(r"[*_~|]"), " "),
    (re.compile(r"!?\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"</?[a-zA-Z][^>]*>"), " "),
    (re.compile(r"https?://\S+"), " "),
]


def tokens(text):
    text = unicodedata.normalize("NFKC", text).lower()
    return Counter(TOKEN_RE.findall(text))


def markdown_tokens(md):
    for pattern, repl in MD_STRIP:
        md = pattern.sub(repl, md)
    return tokens(md)


def recall(reference, produced):
    total = sum(reference.values())
    if not total:
        return None
    hit = sum(min(count, produced.get(word, 0)) for word, count in reference.items())
    return hit / total


NON_PROSE = ("script", "style", "template", "noscript")


def css_text(doc, selector):
    """Visible text under a selector, with script and style bodies removed.

    MediaWiki inlines template CSS inside the article container. Counting it as
    article text would reward a tool for leaking a stylesheet into the Markdown
    and punish one that correctly drops it.
    """
    try:
        nodes = CSSSelector(selector)(doc)
    except Exception:
        return ""
    parts = []
    for node in nodes:
        clone = copy.deepcopy(node)
        for junk in clone.iter(*NON_PROSE):
            junk.getparent().remove(junk) if junk.getparent() is not None else None
        parts.append(clone.text_content())
    return " ".join(parts)


def load_selectors(corpus_dir):
    out = {}
    path = os.path.join(corpus_dir, "selectors.tsv")
    with open(path) as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or not row[0]:
                continue
            slug = row[0]
            article = row[1] if len(row) > 1 else "body"
            boiler = [s for s in (row[2].split("|") if len(row) > 2 and row[2] else []) if s]
            out[slug] = (article, boiler)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="/bench/corpus")
    ap.add_argument("--results", default="/bench/results")
    args = ap.parse_args()

    selectors = load_selectors(args.corpus)
    out_root = os.path.join(args.results, "outputs")
    pages = sorted(p for p in os.listdir(out_root) if os.path.isdir(os.path.join(out_root, p)))

    rows = []
    detail = {}
    missing_probe_files = []

    for slug in pages:
        page_dir = os.path.join(args.corpus, "pages", slug)
        with open(os.path.join(page_dir, "page.html"), encoding="utf-8", errors="replace") as fh:
            doc = lxml_html.fromstring(fh.read())
        article_sel, boiler_sels = selectors.get(slug, ("body", []))
        article_tokens = tokens(css_text(doc, article_sel))
        boiler_raw = tokens(" ".join(css_text(doc, s) for s in boiler_sels))
        boiler_tokens = Counter({w: c for w, c in boiler_raw.items() if w not in article_tokens})

        probe_path = os.path.join(page_dir, "probes.yaml")
        if os.path.isfile(probe_path):
            with open(probe_path) as fh:
                spec = yaml.safe_load(fh) or {}
            probe_list = spec.get("probes", [])
        else:
            missing_probe_files.append(slug)
            probe_list = []

        detail[slug] = {}
        for adapter in ALL:
            md_path = os.path.join(out_root, slug, adapter.name.translate(SAFE).lower() + ".md")
            if not os.path.isfile(md_path):
                continue
            with open(md_path, encoding="utf-8", errors="replace") as fh:
                md = fh.read()

            produced = markdown_tokens(md)
            retention = recall(article_tokens, produced)
            leakage = recall(boiler_tokens, produced)

            results = {}
            per_feature = {f: [0, 0] for f in FEATURES}
            passed = total = weighted_pass = weighted_total = 0
            for probe in probe_list:
                if not applies(probe, adapter.kind):
                    continue
                ok = evaluate(probe, md, adapter.kind)
                weight = probe.get("weight", 1)
                results[probe["id"]] = ok
                total += 1
                weighted_total += weight
                if ok:
                    passed += 1
                    weighted_pass += weight
                bucket = per_feature.setdefault(probe["feature"], [0, 0])
                bucket[1] += 1
                bucket[0] += 1 if ok else 0

            detail[slug][adapter.name] = {
                "probes": results,
                "per_feature": {f: v for f, v in per_feature.items() if v[1]},
            }
            rows.append(
                {
                    "page": slug,
                    "tool": adapter.name,
                    "lang": adapter.lang,
                    "kind": adapter.kind,
                    "ranked": adapter.ranked,
                    "probes_passed": passed,
                    "probes_total": total,
                    "probe_pass_rate": round(weighted_pass / weighted_total, 4) if weighted_total else None,
                    "retention": round(retention, 4) if retention is not None else None,
                    "boilerplate_leakage": round(leakage, 4) if leakage is not None else None,
                    "output_bytes": len(md.encode("utf-8")),
                }
            )

    csv_path = os.path.join(args.results, "scores.csv")
    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with open(os.path.join(args.results, "probe-results.json"), "w") as fh:
        json.dump(detail, fh, indent=2, sort_keys=True)
        fh.write("\n")

    if missing_probe_files:
        print("WARNING: no probes.yaml for: " + ", ".join(missing_probe_files))
    print(f"wrote {csv_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
