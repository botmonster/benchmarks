# HTML to Markdown benchmark results

Corpus: 10 open-license pages. Probes: 273 per tool (some probes apply only to converters or only to extractors).
Repetitions per conversion: 7. Subprocess spawn overhead on this machine: 0.433 ms, which is included in the pandoc, Go and Rust timings.

## League table

| # | Tool | Lang | Kind | Probe pass | Retention | Boilerplate | Total ms | Output |
|---|---|---|---|---|---|---|---|---|
| 1 | [html-to-markdown (go)](https://github.com/JohannesKaufmann/html-to-markdown) | Go | converter | 96% (263/273) | 94% | 76% | 189 | 982 KB |
| 2 | [markdownify](https://github.com/matthewwithanm/python-markdownify) | Python | converter | 96% (262/273) | 94% | 76% | 1662 | 837 KB |
| 3 | [html-to-markdown (py)](https://github.com/xberg-io/html-to-markdown) | Python | converter | 93% (254/273) | 94% | 47% | 82 | 1011 KB |
| 4 | [htmd](https://github.com/letmutex/htmd) | Rust | converter | 92% (251/273) | 94% | 77% | 108 | 1222 KB |
| 5 | [turndown](https://github.com/mixmark-io/turndown) | JavaScript | converter | 90% (246/273) | 94% | 77% | 562 | 1279 KB |
| 6 | [markitdown](https://github.com/microsoft/markitdown) | Python | extractor | 90% (246/273) | 94% | 68% | 2039 | 860 KB |
| 7 | [node-html-markdown](https://github.com/crosstype/node-html-markdown) | JavaScript | converter | 89% (242/273) | 94% | 76% | 3054 | 1046 KB |
| 8 | [html2text](https://github.com/Alir3z4/html2text) | Python | converter | 88% (240/273) | 94% | 76% | 632 | 901 KB |
| 9 | [trafilatura](https://github.com/adbar/trafilatura) | Python | extractor | 81% (221/273) | 88% | 0% | 1008 | 593 KB |
| 10 | [pandoc](https://github.com/jgm/pandoc) | Haskell | converter | 76% (208/273) | 89% | 18% | 4497 | 746 KB |

Boilerplate is the share of nav, header and footer wording that reached the output. High is expected for a converter and bad for an extractor.

### Scored but not ranked

| Tool | Probe pass | Retention | Total ms | Why |
|---|---|---|---|---|
| turndown (no gfm plugin) | 90% (245/273) | 94% | 474 | stock turndown with no plugins, scored to show what the plugin buys you |
| pandoc (default gfm) | 65% (177/273) | 97% | 6118 | plain --to=gfm, which passes tables, figures and pre blocks through as raw HTML |

## Pass rate by HTML feature

| Tool | headings | tables | code | lists | links | images | inline | escaping | footnotes | math | entities | structure | boilerplate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| html-to-markdown (go) | 100% | 86% | 98% | 100% | 96% | 100% | 90% | 92% | 100% | 75% | 100% | 100% | 100% |
| markdownify | 100% | 100% | 88% | 100% | 96% | 92% | 90% | 100% | 100% | 75% | 100% | 100% | 100% |
| html-to-markdown (py) | 100% | 100% | 93% | 95% | 91% | 100% | 90% | 100% | 100% | 62% | 100% | 100% | 53% |
| htmd | 100% | 76% | 73% | 100% | 100% | 100% | 90% | 100% | 100% | 75% | 100% | 95% | 100% |
| turndown | 100% | 76% | 80% | 100% | 87% | 100% | 90% | 92% | 100% | 50% | 88% | 93% | 100% |
| markitdown | 100% | 100% | 88% | 100% | 87% | 100% | 90% | 100% | 100% | 75% | 100% | 100% | 12% |
| node-html-markdown | 100% | 90% | 66% | 95% | 78% | 100% | 70% | 100% | 83% | 75% | 100% | 100% | 100% |
| html2text | 100% | 43% | 93% | 84% | 70% | 100% | 90% | 100% | 50% | 75% | 100% | 100% | 94% |
| trafilatura | 72% | 95% | 71% | 68% | 78% | 54% | 90% | 100% | 100% | 50% | 88% | 93% | 100% |
| pandoc | 93% | 48% | 34% | 100% | 87% | 85% | 95% | 83% | 67% | 62% | 100% | 100% | 35% |

## Per page

### 01-wikipedia-markdown

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 90% | 96% | 68% | 16.6 |
| markdownify | 95% | 96% | 69% | 126.4 |
| html-to-markdown (py) | 95% | 96% | 41% | 5.4 |
| htmd | 90% | 97% | 74% | 9.5 |
| turndown | 83% | 97% | 74% | 42.7 |
| markitdown | 95% | 96% | 0% | 159.5 |
| node-html-markdown | 90% | 96% | 69% | 149.1 |
| html2text | 88% | 96% | 68% | 55.8 |
| trafilatura | 88% | 87% | 0% | 97.0 |
| pandoc | 48% | 82% | 15% | 322.3 |

### 02-wikibooks-latex-mathematics

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 100% | 96% | 67% | 25.4 |
| markdownify | 94% | 96% | 67% | 314.0 |
| html-to-markdown (py) | 91% | 98% | 44% | 8.0 |
| htmd | 83% | 96% | 70% | 16.7 |
| turndown | 69% | 97% | 70% | 109.6 |
| markitdown | 89% | 96% | 67% | 329.5 |
| node-html-markdown | 83% | 96% | 67% | 711.0 |
| html2text | 94% | 96% | 67% | 102.3 |
| trafilatura | 77% | 90% | 0% | 158.8 |
| pandoc | 60% | 81% | 15% | 420.3 |

### 03-mdn-html-table

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 91% | 54% | 35% | 14.9 |
| markdownify | 97% | 54% | 34% | 100.0 |
| html-to-markdown (py) | 94% | 53% | 7% | 7.5 |
| htmd | 89% | 54% | 31% | 8.5 |
| turndown | 91% | 54% | 31% | 35.8 |
| markitdown | 91% | 54% | 34% | 138.1 |
| node-html-markdown | 91% | 54% | 34% | 151.9 |
| html2text | 91% | 54% | 34% | 55.1 |
| trafilatura | 97% | 44% | 0% | 33.2 |
| pandoc | 80% | 53% | 0% | 536.8 |

### 04-python-docs-asyncio-task

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 100% | 97% | 100% | 15.0 |
| markdownify | 100% | 97% | 100% | 150.4 |
| html-to-markdown (py) | 94% | 97% | 94% | 10.2 |
| htmd | 94% | 97% | 100% | 8.9 |
| turndown | 88% | 97% | 100% | 44.9 |
| markitdown | 94% | 97% | 100% | 190.2 |
| node-html-markdown | 79% | 96% | 100% | 44.2 |
| html2text | 79% | 97% | 100% | 54.4 |
| trafilatura | 68% | 96% | 0% | 119.4 |
| pandoc | 68% | 96% | 1% | 270.8 |

### 05-rust-book-vectors

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 97% | 99% | 100% | 3.5 |
| markdownify | 93% | 99% | 100% | 15.4 |
| html-to-markdown (py) | 100% | 99% | 100% | 1.3 |
| htmd | 100% | 99% | 100% | 2.3 |
| turndown | 100% | 99% | 100% | 5.4 |
| markitdown | 90% | 99% | 100% | 37.4 |
| node-html-markdown | 100% | 99% | 100% | 3.3 |
| html2text | 90% | 99% | 100% | 6.2 |
| trafilatura | 90% | 99% | 0% | 8.7 |
| pandoc | 90% | 99% | 0% | 351.2 |

### 06-kubernetes-pod-lifecycle

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 100% | 99% | 97% | 33.7 |
| markdownify | 94% | 99% | 97% | 276.9 |
| html-to-markdown (py) | 94% | 99% | 2% | 16.1 |
| htmd | 100% | 98% | 97% | 15.1 |
| turndown | 100% | 99% | 97% | 92.0 |
| markitdown | 89% | 99% | 97% | 360.3 |
| node-html-markdown | 97% | 99% | 97% | 667.9 |
| html2text | 77% | 99% | 97% | 106.0 |
| trafilatura | 66% | 86% | 0% | 107.4 |
| pandoc | 89% | 99% | 0% | 815.5 |

### 07-gutenberg-alice

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 83% | 100% | - | 12.5 |
| markdownify | 83% | 100% | - | 54.3 |
| html-to-markdown (py) | 83% | 100% | - | 2.8 |
| htmd | 83% | 100% | - | 5.2 |
| turndown | 73% | 100% | - | 23.8 |
| markitdown | 83% | 100% | - | 89.9 |
| node-html-markdown | 77% | 100% | - | 212.1 |
| html2text | 73% | 100% | - | 25.4 |
| trafilatura | 60% | 100% | - | 74.4 |
| pandoc | 80% | 100% | - | 354.9 |

### 08-arxiv-phi3

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 88% | 100% | 100% | 19.5 |
| markdownify | 85% | 100% | 100% | 189.1 |
| html-to-markdown (py) | 78% | 98% | 85% | 6.1 |
| htmd | 88% | 100% | 100% | 11.3 |
| turndown | 82% | 100% | 100% | 58.3 |
| markitdown | 80% | 100% | 100% | 223.6 |
| node-html-markdown | 85% | 100% | 97% | 93.5 |
| html2text | 78% | 100% | 100% | 65.2 |
| trafilatura | 90% | 92% | 0% | 141.1 |
| pandoc | 98% | 98% | 100% | 396.2 |

### 09-wikivoyage-tokyo

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 100% | 100% | 68% | 35.8 |
| markdownify | 100% | 100% | 68% | 316.5 |
| html-to-markdown (py) | 97% | 99% | 43% | 10.6 |
| htmd | 89% | 100% | 68% | 21.4 |
| turndown | 89% | 100% | 68% | 105.3 |
| markitdown | 91% | 100% | 68% | 369.2 |
| node-html-markdown | 94% | 100% | 68% | 985.3 |
| html2text | 94% | 100% | 68% | 127.0 |
| trafilatura | 94% | 89% | 0% | 217.4 |
| pandoc | 83% | 87% | 18% | 729.8 |

### 10-github-readme-markitdown

| Tool | Probe pass | Retention | Boilerplate | Median ms |
|---|---|---|---|---|
| html-to-markdown (go) | 100% | 98% | 50% | 11.8 |
| markdownify | 100% | 98% | 50% | 119.2 |
| html-to-markdown (py) | 94% | 97% | 7% | 14.2 |
| htmd | 76% | 98% | 50% | 9.3 |
| turndown | 100% | 98% | 50% | 44.4 |
| markitdown | 94% | 98% | 50% | 141.1 |
| node-html-markdown | 76% | 98% | 50% | 35.9 |
| html2text | 88% | 98% | 50% | 35.0 |
| trafilatura | 76% | 95% | 0% | 50.7 |
| pandoc | 73% | 97% | 11% | 299.5 |

## Probes nothing passed

- `03-mdn-html-table` / `code-fence-language-html`
