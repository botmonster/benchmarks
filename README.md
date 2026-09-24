# botmonster.com benchmarks

Reproducible benchmarks behind [botmonster.com](https://botmonster.com) blog posts.

Every time a post publishes measured numbers, the exact scripts that produced them land here, in one folder per post. Each folder contains:

- a `README.md` describing what is tested, the methodology, and a link to the blog post where the results are discussed
- a single `run.sh` that installs everything it needs (into a local `.tools/` directory, no sudo, no system changes) and walks you through every test stage
- the raw results from the author's run, for provenance

## Benchmarks

| Folder | Blog post | What is benchmarked |
|---|---|---|
| [bun-vs-deno-vs-nodejs](bun-vs-deno-vs-nodejs/) | [Bun vs Deno vs Node.js: which JavaScript runtime actually wins in 2026?](https://botmonster.com/web-dev/bun-vs-deno-vs-nodejs-javascript-runtime-2026/) | HTTP throughput (single core), process cold start, cold/warm package install, test runners, JSON parse/stringify, idle memory |
| [cache-key-leak](cache-key-leak/) | [An Aladdin Connect cache bug leaked strangers' garage doors](https://botmonster.com/smart-home/an-aladdin-connect-cache-bug-leaked-strangers-garage-doors/) | A stock nginx cache with the default key serving one user's API response to everyone, a 40-client polling simulation of the rotating-stranger pattern, and two fixes |
| [duckdb-csv-parquet-analytics](duckdb-csv-parquet-analytics/) | [DuckDB is absurdly good at crunching gigabytes with no database server](https://botmonster.com/coding/duckdb-developers-analyze-csv-parquet-no-server/) | DuckDB vs Pandas vs Polars (filter/group-by/join), CSV vs Parquet scan, out-of-core sort under a memory limit, direct Parquet query with no import |
| [html-to-markdown-converters](html-to-markdown-converters/) | [Best 10 HTML to Markdown converters in 2026](https://botmonster.com/coding/best-10-html-to-markdown-converters-in-2026/) | feature-probe fidelity across 10 open-license pages, text retention, boilerplate leakage, conversion speed |
| [object-storage-for-saas](object-storage-for-saas/) | [The best object storage for SaaS in 2026](https://botmonster.com/web-dev/the-best-object-storage-for-saas-in-2026/) | monthly cost of three SaaS workloads on eight providers |

## Replicating

Each folder is self-contained. On Ubuntu:

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/<folder>
./run.sh
```

The script guides you through each stage and prints a summary table at the end. See the folder's README for flags and prerequisites.

One exception to the "no system changes" rule: `html-to-markdown-converters` needs Docker, because it puts ten tools written in six languages into one image instead of installing six toolchains on your machine.

## License

[MIT](LICENSE)
