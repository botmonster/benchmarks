# HTML to Markdown: ten converters against ten real pages

Reproducible benchmark behind [Best 10 HTML to Markdown converters in 2026](https://botmonster.com/coding/best-10-html-to-markdown-converters-in-2026/).

Ten tools convert the same ten scraped, open-license web pages. Each output is checked against 273 hand-written probes that name a specific HTML feature on a specific page and state what correct Markdown for it looks like, so a failure points at a feature rather than at a vague quality score. Two text measures sit alongside the probes: how much of the article's own wording survived, and how much of the site's nav and footer came with it.

Everything runs inside one Docker image that holds all ten tools. Nothing is installed on your machine.

## What is tested

1. **Probe pass rate** ([`harness/probes.py`](harness/probes.py), [`harness/score.py`](harness/score.py)). 273 assertions across 13 feature groups: headings, tables, code, lists, links, images, inline formatting, escaping, footnotes, math, entities, document structure and boilerplate. Each probe is written against the committed HTML, not guessed.
2. **Text retention.** Word-token recall of the article container's visible text, with `script` and `style` bodies excluded. Catches a tool that passes the probes but quietly drops a third of the body.
3. **Boilerplate leakage.** The same recall measure over nav, header and footer wording that does not also appear in the article. High is correct for a converter and wrong for an extractor.
4. **Speed** ([`harness/run_all.py`](harness/run_all.py)). Median of 7 timed repetitions after a warmup, per page and in total.
5. **Output size.** Total bytes of Markdown produced across the corpus.

Probes tagged `boilerplate` invert for extractors: a converter passes by keeping the chrome, an extractor passes by dropping it, so neither class is punished for doing its job.

## The ten tools

| Tool | Lang | Kind | Version | How it is invoked |
|---|---|---|---|---|
| [turndown](https://github.com/mixmark-io/turndown) | JavaScript | converter | 7.2.4 | with `turndown-plugin-gfm`, which its own docs point you at for tables |
| [node-html-markdown](https://github.com/crosstype/node-html-markdown) | JavaScript | converter | 2.0.0 | `bulletMarker: '-'`, fenced code |
| [markdownify](https://github.com/matthewwithanm/python-markdownify) | Python | converter | 1.2.3 | ATX headings, `-` bullets |
| [html2text](https://github.com/Alir3z4/html2text) | Python | converter | 2025.4.15 | library defaults except `body_width = 0` |
| [html-to-markdown](https://github.com/xberg-io/html-to-markdown) | Python | converter | 3.14.3 | ATX headings, metadata extraction off |
| [html-to-markdown](https://github.com/JohannesKaufmann/html-to-markdown) | Go | converter | 2.5.2 | `--plugin-table --plugin-strikethrough` |
| [htmd](https://github.com/letmutex/htmd) | Rust | converter | 0.5.1 | CLI defaults |
| [pandoc](https://github.com/jgm/pandoc) | Haskell | converter | 3.11 | `--to=gfm-raw_html`, see the note below |
| [trafilatura](https://github.com/adbar/trafilatura) | Python | extractor | 2.2.0 | markdown output, tables, links, images and formatting all on |
| [markitdown](https://github.com/microsoft/markitdown) | Python | extractor | 0.1.7 | defaults, plugins off |

Two tools are also scored in a second configuration, reported but not ranked, because the flag makes a large difference and readers deserve to see the size of it: **turndown with no plugins**, and **pandoc with plain `--to=gfm`**.

Plain `--to=gfm` lets pandoc pass anything it cannot express straight through as raw HTML. That is not a conversion and it is not what the other nine tools do, so the ranked run subtracts the extension.

Exact versions are pinned in [`versions.env`](versions.env) and baked into the image as build arguments.

## Test corpus

Ten real pages, scraped whole with their nav, header, sidebar and footer intact, so the boilerplate measure means something. Each fixture ships its raw HTML, a `meta.json` with provenance, and its own `probes.yaml`. Full attribution is in [`corpus/LICENSES.md`](corpus/LICENSES.md).

| # | Page | License | Fixture | What it stresses |
|---|---|---|---|---|
| 01 | [Wikipedia, "Markdown"](https://en.wikipedia.org/wiki/Markdown) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | [`page.html`](corpus/pages/01-wikipedia-markdown/page.html) | infobox tables, 73 footnote refs, code samples inside table cells, inline template CSS |
| 02 | [Wikibooks, "LaTeX/Mathematics"](https://en.wikibooks.org/wiki/LaTeX/Mathematics) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | [`page.html`](corpus/pages/02-wikibooks-latex-mathematics/page.html) | 341 MathML elements, 81 tables, LaTeX source blocks full of backslashes |
| 03 | [MDN, the `<table>` element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table) | [CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/) | [`page.html`](corpus/pages/03-mdn-html-table/page.html) | an H1 containing angle brackets, 20 definition lists, 11 `details` elements, syntax-highlight span soup |
| 04 | [Python docs, "Coroutines and Tasks"](https://docs.python.org/3/library/asyncio-task.html) | [PSF License 2.0](https://docs.python.org/3/license.html) | [`page.html`](corpus/pages/04-python-docs-asyncio-task/page.html) | 41 API signatures as definition lists, doctest blocks, admonitions |
| 05 | [The Rust Book, "Storing Lists of Values with Vectors"](https://doc.rust-lang.org/book/ch08-01-vectors.html) | [MIT or Apache-2.0](https://github.com/rust-lang/book/blob/main/LICENSE-MIT) | [`page.html`](corpus/pages/05-rust-book-vectors/page.html) | standalone `language-rust` code blocks, `vec![1, 2, 3]` which reads as link syntax |
| 06 | [Kubernetes, "Pod Lifecycle"](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [`page.html`](corpus/pages/06-kubernetes-pod-lifecycle/page.html) | a five-column matrix with colons in its headers, YAML blocks, `details` elements, an unquoted `src` |
| 07 | [Project Gutenberg, *Alice's Adventures in Wonderland*](https://www.gutenberg.org/files/11/11-h/11-h.htm) | [Public domain](https://www.gutenberg.org/policy/permission.html) | [`page.html`](corpus/pages/07-gutenberg-alice/page.html) | poems held together by `br` tags, a shaped `pre` block, curly quotes, a table used as a contents list |
| 08 | [arXiv, "Phi-3 Technical Report"](https://arxiv.org/html/2404.14219) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | [`page.html`](corpus/pages/08-arxiv-phi3/page.html) | LaTeXML MathML that prints every number twice, 15 figures, tables built from spans, a bibliography |
| 09 | [Wikivoyage, "Tokyo"](https://en.wikivoyage.org/wiki/Tokyo) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | [`page.html`](corpus/pages/09-wikivoyage-tokyo/page.html) | 189 images, a table nested inside a table, Japanese script, template CSS inside the content |
| 10 | [GitHub, the markitdown README](https://github.com/microsoft/markitdown) | [MIT](https://github.com/microsoft/markitdown/blob/main/LICENSE) | [`page.html`](corpus/pages/10-github-readme-markitdown/page.html) | shell blocks containing `|`, `>` and `[all]`, badge images, a capability table, heavy inline SVG chrome |

[`corpus/fetch-corpus.sh`](corpus/fetch-corpus.sh) re-downloads all ten from [`corpus/sources.tsv`](corpus/sources.tsv). You do not need to run it: the fixtures are committed, and the probes are written against these exact copies.

## Replicating

You need Docker and python3. Nothing else.

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/html-to-markdown-converters
./run.sh                 # interactive stage gates
./run.sh --yes           # no prompts
./run.sh --yes --skip-build   # reuse the image you already built
./run.sh --yes --reps 1       # one timed pass instead of seven, much faster
./run.sh --latest        # newest published version of every tool instead of the pins
```

Five stages: build the image, verify the fixtures and print versions, convert, score, report. Each one can be skipped at its prompt.

Files: [`Dockerfile`](Dockerfile) builds the Go and Rust binaries in their own stages and assembles everything onto `python:3.12-slim`. [`run.sh`](run.sh) drives the stages. [`harness/adapters/`](harness/adapters/) wraps each tool behind one `convert(html, base_url)` call; the JavaScript pair runs through a single long-lived Node worker so startup is paid once. [`harness/probes.py`](harness/probes.py) is the probe engine, [`harness/score.py`](harness/score.py) the scorer, [`harness/report.py`](harness/report.py) the report and charts.

## Author's results

**Machine:** 24-core x86_64 Linux, 62 GB RAM, Docker 29.8.1, image built on `python:3.12-slim-bookworm` with Node 22. **Run:** 2026-09-20, `./run.sh --yes`, 7 repetitions per conversion. Full output in [`results/report.md`](results/report.md), machine-readable numbers in [`results/scores.csv`](results/scores.csv), [`results/timings.json`](results/timings.json) and [`results/probe-results.json`](results/probe-results.json).

The converted Markdown itself is not committed. It is 120 files and about 11 MB, which is twelve copies of the same ten articles, and `./run.sh --yes` regenerates it byte for byte into `results/outputs/<page>/<tool>.md`.

| # | Tool | Lang | Probe pass | Retention | Boilerplate | Total ms | Output |
|---|---|---|---|---|---|---|---|
| 1 | html-to-markdown (Go) | Go | 96% (263/273) | 94% | 76% | 189 | 982 KB |
| 2 | markdownify | Python | 96% (262/273) | 94% | 76% | 1662 | 837 KB |
| 3 | html-to-markdown (Python) | Python | 93% (254/273) | 94% | 47% | 82 | 1011 KB |
| 4 | htmd | Rust | 92% (251/273) | 94% | 77% | 108 | 1222 KB |
| 5 | turndown | JavaScript | 90% (246/273) | 94% | 77% | 562 | 1279 KB |
| 6 | markitdown | Python | 90% (246/273) | 94% | 68% | 2039 | 860 KB |
| 7 | node-html-markdown | JavaScript | 89% (242/273) | 94% | 76% | 3054 | 1046 KB |
| 8 | html2text | Python | 88% (240/273) | 94% | 76% | 632 | 901 KB |
| 9 | trafilatura | Python | 81% (221/273) | 88% | 0% | 1008 | 593 KB |
| 10 | pandoc | Haskell | 76% (208/273) | 89% | 18% | 4497 | 746 KB |

Not ranked, same probes:

| Tool | Probe pass | Retention | Total ms |
|---|---|---|---|
| turndown with no plugins | 90% (245/273) | 94% | 474 |
| pandoc with plain `--to=gfm` | 65% (177/273) | 96% | 6118 |

**What the numbers say:**

- **The Go tool and markdownify tie at 96%**, and the Go binary does it 9 times faster. The Python `html-to-markdown` is the fastest of all at 82 ms for the whole corpus, four percentage points behind.
- **Tables are where tools separate.** Per-feature pass rates run from 100% (markdownify, the Python `html-to-markdown`, markitdown) down to 43% for html2text, which emits a pipe layout that is not GFM.
- **Code blocks separate them again.** The Go tool passes 98% of code probes; node-html-markdown 66%, pandoc 34%. The most common failure is a `pre` sitting inside a table cell, which GFM cannot hold and most tools flatten to a single line.
- **Nothing reads MDN's language hint.** `class="brush: html"` is the one probe out of 273 that no tool passes. Every tool reads `class="language-x"` and no tool reads MDN's older convention, so MDN code fences come out untagged.
- **arXiv MathML prints every number twice.** LaTeXML emits the value as MathML and again as a fallback, so `3072` reads as `30723072` in eight of the ten tools. Only pandoc and trafilatura avoid it.
- **`br` tags inside a poem are lost by nine tools out of ten.** Only pandoc keeps *Alice* readable as verse; everyone else joins the lines into prose.
- **turndown needs its plugin more than its docs suggest.** Without `turndown-plugin-gfm` it produced zero fenced code blocks on the GitHub README, against 54 with it.
- **The extractor/converter split is visible in one column.** trafilatura leaks 0% of the site chrome and pays for it with the lowest retention (88%) and pass rate (81%). markitdown is sold as an extractor but leaks 68% of the boilerplate, which puts it with the converters in practice.
- **pandoc's default is the trap.** Plain `--to=gfm` scores 65% because it passes tables, figures and `pre` blocks through as raw HTML; `--to=gfm-raw_html` lifts it to 76%. It is also the slowest tool in the set either way.

Absolute millisecond numbers are hardware-dependent; treat them as relative. The pandoc, Go and Rust figures are subprocess calls and include about 0.4 ms of process start each. What holds across machines is the ordering and the size of the gaps.

## License

[MIT](../LICENSE). The test corpus is third-party content under its own licenses, listed in [`corpus/LICENSES.md`](corpus/LICENSES.md).
