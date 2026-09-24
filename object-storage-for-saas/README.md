# Object storage for SaaS: cost on three workloads

Reproducible numbers behind [The best object storage for SaaS in 2026](https://botmonster.com/web-dev/the-best-object-storage-for-saas-in-2026/).

## What is tested

**Monthly cost** ([`cost.py`](cost.py)). Eight providers priced on three SaaS workloads with each provider's own published rates, pinned in the script as constants read on 2026-09-24. No API calls, no accounts.

### Workloads

| Workload | Stored | Downloaded / month | Uploads / month | Reads / month |
|---|---|---|---|---|
| Early-stage | 20 GB | 50 GB | 100k | 1M |
| Document | 200 GB | 300 GB | 1M | 10M |
| Media | 1 TB | 10 TB | 2M | 50M |

### Pricing rules modelled

- **AWS S3 Standard, us-east-1:** $0.023/GB, egress $0.09/GB after 100 GB free (tiered down above 10 TB), $5.00 per 1M writes, $0.40 per 1M reads.
- **Cloudflare R2 Standard:** $0.015/GB, free egress, $4.50 per 1M writes, $0.36 per 1M reads, free tier of 10 GB, 1M writes and 10M reads, usage rounded up to the next unit.
- **Backblaze B2:** $6.95/TB, first 10 GB free, egress free up to 3x average stored then $0.01/GB, Class A/B/C calls free.
- **Wasabi pay-as-you-go:** $7.99/TB with a 1 TB minimum, no egress or request fees, flagged when monthly egress exceeds stored data (outside Wasabi's free egress policy).
- **Tigris Standard:** $0.02/GB, free egress, $0.005 per 1k writes, $0.0005 per 1k reads, free 5 GB, 10k writes and 100k reads.
- **Hetzner Object Storage:** $7.99 base including 1 TB stored and 1 TB egress, $1.20 per extra TB of egress, requests free. The extra-storage rate is not modelled; every workload stays at or under 1 TB.
- **Upstash Blob, pay-as-you-go:** $0.02/GB stored, $0.02/GB egress, $4.50 per 1M advanced ops, $0.30 per 1M simple ops, no free allowance.
- **Vercel Blob, on-demand (iad1):** $0.023/GB, $0.05/GB transfer, $5.00 per 1M advanced ops, $0.40 per 1M simple ops, and $0.06/GB Fast Origin Transfer on cache misses. Assumes Vercel's own example hit ratio of 70%, so 30% of reads are billed. The Pro seat fee is not included.

## Replicating

You need any Linux or macOS machine with python3. No dependencies, no sudo, no Docker.

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/object-storage-for-saas
./run.sh
```

## Author's results

**Machine:** 24-core x86_64 Linux, 62 GB RAM, Python 3.12. **Run:** 2026-09-24, `./run.sh`.

Cost table from [`results/cost.md`](results/cost.md):

| Provider | Early-stage | Document | Media |
|---|---|---|---|
| Cloudflare R2 | $0.15 | $2.85 | $33.75 |
| Backblaze B2 | $0.07 | $1.32 | $76.88 |
| Hetzner | $7.99 | $7.99 | $18.79 |
| Wasabi | $7.99, over egress rule | $7.99, over egress rule | $7.99, over egress rule |
| Tigris | $1.20 | $13.80 | $54.80 |
| Upstash Blob | $2.15 | $17.50 | $244.00 |
| Vercel Blob | $4.48 | $31.20 | $719.00 |
| AWS S3 | $1.36 | $31.60 | $944.00 |
