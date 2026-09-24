#!/usr/bin/env python3
import math

GB_PER_TB = 1_000

WORKLOADS = {
    "Early-stage": {
        "stored_gb": 20,
        "egress_gb": 50,
        "million_writes": 0.1,
        "million_reads": 1,
    },
    "Document": {
        "stored_gb": 200,
        "egress_gb": 300,
        "million_writes": 1,
        "million_reads": 10,
    },
    "Media": {
        "stored_gb": 1_000,
        "egress_gb": 10_000,
        "million_writes": 2,
        "million_reads": 50,
    },
}

AWS_S3_USD_PER_GB_STORED = 0.023
AWS_S3_FREE_EGRESS_GB = 100
AWS_S3_EGRESS_TIERS_GB_AND_USD_PER_GB = [
    (10_240, 0.09),
    (40_960, 0.085),
    (102_400, 0.07),
    (math.inf, 0.05),
]
AWS_S3_USD_PER_MILLION_WRITES = 5.00
AWS_S3_USD_PER_MILLION_READS = 0.40

R2_USD_PER_GB_STORED = 0.015
R2_FREE_GB_STORED = 10
R2_USD_PER_MILLION_WRITES = 4.50
R2_FREE_MILLION_WRITES = 1
R2_USD_PER_MILLION_READS = 0.36
R2_FREE_MILLION_READS = 10

B2_USD_PER_TB_STORED = 6.95
B2_FREE_GB_STORED = 10
B2_FREE_EGRESS_MULTIPLE_OF_STORED = 3
B2_USD_PER_GB_EGRESS_OVER_FREE = 0.01

WASABI_USD_PER_TB_STORED = 7.99
WASABI_MINIMUM_TB_BILLED = 1

TIGRIS_USD_PER_GB_STORED = 0.02
TIGRIS_FREE_GB_STORED = 5
TIGRIS_USD_PER_MILLION_WRITES = 5.00
TIGRIS_FREE_MILLION_WRITES = 0.01
TIGRIS_USD_PER_MILLION_READS = 0.50
TIGRIS_FREE_MILLION_READS = 0.1

HETZNER_BASE_USD_INCLUDING_1_TB_STORED_AND_EGRESS = 7.99
HETZNER_EGRESS_GB_INCLUDED = 1_000
HETZNER_USD_PER_TB_EXTRA_EGRESS = 1.20

UPSTASH_USD_PER_GB_STORED = 0.02
UPSTASH_USD_PER_GB_EGRESS = 0.02
UPSTASH_USD_PER_MILLION_WRITES = 4.50
UPSTASH_USD_PER_MILLION_READS = 0.30

VERCEL_USD_PER_GB_STORED = 0.023
VERCEL_USD_PER_GB_TRANSFER = 0.05
VERCEL_USD_PER_GB_ORIGIN_TRANSFER_ON_CACHE_MISS = 0.06
VERCEL_CACHE_MISS_RATIO = 0.30
VERCEL_USD_PER_MILLION_WRITES = 5.00
VERCEL_USD_PER_MILLION_READS = 0.40


def over(amount, free):
    return max(0, amount - free)


def aws_s3(stored_gb, egress_gb, million_writes, million_reads):
    billable_egress_gb = over(egress_gb, AWS_S3_FREE_EGRESS_GB)
    egress_usd = 0
    for tier_size_gb, usd_per_gb in AWS_S3_EGRESS_TIERS_GB_AND_USD_PER_GB:
        tier_gb = min(billable_egress_gb, tier_size_gb)
        egress_usd += tier_gb * usd_per_gb
        billable_egress_gb -= tier_gb
    return (
        stored_gb * AWS_S3_USD_PER_GB_STORED
        + egress_usd
        + million_writes * AWS_S3_USD_PER_MILLION_WRITES
        + million_reads * AWS_S3_USD_PER_MILLION_READS
    )


def cloudflare_r2(stored_gb, egress_gb, million_writes, million_reads):
    return (
        math.ceil(over(stored_gb, R2_FREE_GB_STORED)) * R2_USD_PER_GB_STORED
        + math.ceil(over(million_writes, R2_FREE_MILLION_WRITES))
        * R2_USD_PER_MILLION_WRITES
        + math.ceil(over(million_reads, R2_FREE_MILLION_READS))
        * R2_USD_PER_MILLION_READS
    )


def backblaze_b2(stored_gb, egress_gb, million_writes, million_reads):
    free_egress_gb = B2_FREE_EGRESS_MULTIPLE_OF_STORED * stored_gb
    return (
        over(stored_gb, B2_FREE_GB_STORED) / GB_PER_TB * B2_USD_PER_TB_STORED
        + over(egress_gb, free_egress_gb) * B2_USD_PER_GB_EGRESS_OVER_FREE
    )


def wasabi(stored_gb, egress_gb, million_writes, million_reads):
    billed_tb = max(WASABI_MINIMUM_TB_BILLED, stored_gb / GB_PER_TB)
    return billed_tb * WASABI_USD_PER_TB_STORED


def tigris(stored_gb, egress_gb, million_writes, million_reads):
    return (
        over(stored_gb, TIGRIS_FREE_GB_STORED) * TIGRIS_USD_PER_GB_STORED
        + over(million_writes, TIGRIS_FREE_MILLION_WRITES)
        * TIGRIS_USD_PER_MILLION_WRITES
        + over(million_reads, TIGRIS_FREE_MILLION_READS)
        * TIGRIS_USD_PER_MILLION_READS
    )


def hetzner(stored_gb, egress_gb, million_writes, million_reads):
    extra_egress_tb = over(egress_gb, HETZNER_EGRESS_GB_INCLUDED) / GB_PER_TB
    return (
        HETZNER_BASE_USD_INCLUDING_1_TB_STORED_AND_EGRESS
        + extra_egress_tb * HETZNER_USD_PER_TB_EXTRA_EGRESS
    )


def upstash_blob(stored_gb, egress_gb, million_writes, million_reads):
    return (
        stored_gb * UPSTASH_USD_PER_GB_STORED
        + egress_gb * UPSTASH_USD_PER_GB_EGRESS
        + million_writes * UPSTASH_USD_PER_MILLION_WRITES
        + million_reads * UPSTASH_USD_PER_MILLION_READS
    )


def vercel_blob(stored_gb, egress_gb, million_writes, million_reads):
    return (
        stored_gb * VERCEL_USD_PER_GB_STORED
        + egress_gb * VERCEL_USD_PER_GB_TRANSFER
        + egress_gb
        * VERCEL_CACHE_MISS_RATIO
        * VERCEL_USD_PER_GB_ORIGIN_TRANSFER_ON_CACHE_MISS
        + million_writes * VERCEL_USD_PER_MILLION_WRITES
        + million_reads * VERCEL_CACHE_MISS_RATIO * VERCEL_USD_PER_MILLION_READS
    )


PROVIDERS = {
    "Cloudflare R2": cloudflare_r2,
    "Backblaze B2": backblaze_b2,
    "Hetzner": hetzner,
    "Wasabi": wasabi,
    "Tigris": tigris,
    "Upstash Blob": upstash_blob,
    "Vercel Blob": vercel_blob,
    "AWS S3": aws_s3,
}


def cell(provider, workload):
    total = f"${PROVIDERS[provider](**workload):.2f}"
    if provider == "Wasabi" and workload["egress_gb"] > workload["stored_gb"]:
        total += ", over egress rule"
    return total


print("| Provider | " + " | ".join(WORKLOADS) + " |")
print("|---|" + "---|" * len(WORKLOADS))
for provider in PROVIDERS:
    print(
        f"| {provider} | "
        + " | ".join(cell(provider, w) for w in WORKLOADS.values())
        + " |"
    )
