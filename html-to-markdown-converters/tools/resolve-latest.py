#!/usr/bin/env python3
"""Print a versions.env with the newest published version of every tool.

Used by run.sh --latest. Queries npm, PyPI, crates.io, the Go module proxy and
the GitHub releases API. Anything that cannot be resolved keeps its pinned
value, so the output is always a complete file.
"""

import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url):
    with urllib.request.urlopen(url, timeout=20) as fh:
        return json.load(fh)


def npm(pkg):
    return get(f"https://registry.npmjs.org/{pkg}/latest")["version"]


def pypi(pkg):
    return get(f"https://pypi.org/pypi/{pkg}/json")["info"]["version"]


def crates(name):
    return get(f"https://crates.io/api/v1/crates/{name}")["crate"]["max_version"]


def gomod(path):
    return get(f"https://proxy.golang.org/{path}/@latest")["Version"]


def github_tag(repo):
    return get(f"https://api.github.com/repos/{repo}/releases/latest")["tag_name"]


RESOLVERS = {
    "TURNDOWN_VERSION": lambda: npm("turndown"),
    "NODE_HTML_MARKDOWN_VERSION": lambda: npm("node-html-markdown"),
    "MARKDOWNIFY_VERSION": lambda: pypi("markdownify"),
    "HTML2TEXT_VERSION": lambda: pypi("html2text"),
    "HTML_TO_MARKDOWN_PY_VERSION": lambda: pypi("html-to-markdown"),
    "TRAFILATURA_VERSION": lambda: pypi("trafilatura"),
    "MARKITDOWN_VERSION": lambda: pypi("markitdown"),
    "HTMD_CLI_VERSION": lambda: crates("htmd-cli"),
    "HTML_TO_MARKDOWN_GO_VERSION": lambda: gomod(
        "github.com/!johannes!kaufmann/html-to-markdown/v2"
    ),
    "PANDOC_VERSION": lambda: github_tag("jgm/pandoc"),
    "LXML_VERSION": lambda: pypi("lxml"),
    "BEAUTIFULSOUP_VERSION": lambda: pypi("beautifulsoup4"),
    "PYYAML_VERSION": lambda: pypi("PyYAML"),
    "CSSSELECT_VERSION": lambda: pypi("cssselect"),
}


def main():
    pinned = {}
    with open(os.path.join(HERE, "versions.env")) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                pinned[key] = value

    for key, resolve in RESOLVERS.items():
        try:
            pinned[key] = re.sub(r"^v(?=\d)", "", resolve()) if key != "HTML_TO_MARKDOWN_GO_VERSION" else resolve()
        except Exception as exc:
            print(f"# keeping pinned {key}={pinned.get(key)} ({exc})", file=sys.stderr)

    for key, value in pinned.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
