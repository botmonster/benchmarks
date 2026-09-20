"""pandoc, the Go html2markdown, and the Rust htmd, each a subprocess.

Their timings include process start. run_all.py measures that overhead
separately so the README can state how much of each number is spawn cost.
"""

import re
import subprocess

from .base import Adapter


def _run(argv, html):
    proc = subprocess.run(
        argv,
        input=html.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{argv[0]} exited {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[:400]}")
    return proc.stdout.decode("utf-8", "replace")


def _pandoc(html, base_url):
    """gfm-raw_html, not plain gfm.

    Plain gfm lets pandoc pass anything it cannot express straight through as
    raw HTML, which is not a conversion and is not what the other nine tools
    do. Subtracting the raw_html extension forces it to convert or drop.
    """
    return _run(
        ["pandoc", "--from=html", "--to=gfm-raw_html", "--wrap=none", "--markdown-headings=atx"],
        html,
    )


def _pandoc_default(html, base_url):
    return _run(
        ["pandoc", "--from=html", "--to=gfm", "--wrap=none", "--markdown-headings=atx"],
        html,
    )


def _go_html2markdown(html, base_url):
    return _run(
        ["html2markdown", "--domain", base_url, "--plugin-table", "--plugin-strikethrough"],
        html,
    )


def _htmd(html, base_url):
    return _run(["htmd"], html)


def _cli_version(argv, pattern=r"(\d+[\w.+-]*)"):
    def get():
        try:
            out = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            text = out.stdout.decode("utf-8", "replace")
        except FileNotFoundError:
            return "unknown"
        match = re.search(pattern, text)
        return match.group(1) if match else text.strip().splitlines()[0][:40]

    return get


ADAPTERS = [
    Adapter(
        name="pandoc",
        kind="converter",
        lang="Haskell",
        repo="https://github.com/jgm/pandoc",
        convert=_pandoc,
        version_fn=_cli_version(["pandoc", "--version"]),
        notes="run as --to=gfm-raw_html so it converts instead of passing HTML through",
    ),
    Adapter(
        name="pandoc (default gfm)",
        kind="converter",
        lang="Haskell",
        repo="https://github.com/jgm/pandoc",
        convert=_pandoc_default,
        version_fn=_cli_version(["pandoc", "--version"]),
        ranked=False,
        notes="plain --to=gfm, which passes tables, figures and pre blocks through as raw HTML",
    ),
    Adapter(
        name="html-to-markdown (go)",
        kind="converter",
        lang="Go",
        repo="https://github.com/JohannesKaufmann/html-to-markdown",
        convert=_go_html2markdown,
        version_fn=_cli_version(["html2markdown", "--version"], r"GitVersion:\s*v?(\S+)"),
    ),
    Adapter(
        name="htmd",
        kind="converter",
        lang="Rust",
        repo="https://github.com/letmutex/htmd",
        convert=_htmd,
        version_fn=_cli_version(["htmd", "--version"]),
    ),
]
