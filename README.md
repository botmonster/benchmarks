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

## Replicating

Each folder is self-contained. On Ubuntu:

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/<folder>
./run.sh
```

The script guides you through each stage and prints a summary table at the end. See the folder's README for flags and prerequisites.

## License

[MIT](LICENSE)
