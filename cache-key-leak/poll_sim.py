import argparse
import csv
import json
import random
import statistics
import threading
import time
import urllib.request
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:18080/v1/devices")
parser.add_argument("--clients", type=int, default=20)
parser.add_argument("--interval", type=float, default=1.0)
parser.add_argument("--duration", type=float, default=60.0)
parser.add_argument("--jitter", type=float, default=0.2)
parser.add_argument("--csv", default="results/poll-sim.csv")
args = parser.parse_args()

observations = []
lock = threading.Lock()
start = time.time()


def poll(client):
    token = f"token-{client}"
    time.sleep(random.uniform(0, args.interval))
    next_at = time.time()
    while time.time() - start < args.duration:
        req = urllib.request.Request(
            args.url, headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as resp:
            status = resp.headers.get("X-Cache-Status", "-")
            account = json.load(resp)["account"]
        with lock:
            observations.append(
                (round(time.time() - start, 3), client, account, status)
            )
        next_at += args.interval + random.uniform(0, args.jitter)
        time.sleep(max(0.0, next_at - time.time()))


clients = [f"household{n:02d}" for n in range(1, args.clients + 1)]
threads = [threading.Thread(target=poll, args=(c,)) for c in clients]
for t in threads:
    t.start()
for t in threads:
    t.join()

observations.sort()
with open(args.csv, "w", newline="") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(["t_seconds", "client", "account_returned", "x_cache_status"])
    writer.writerows(observations)

total = len(observations)
own = sum(1 for _, c, a, _ in observations if c == a)
foreign = total - own

runs = []
for t, _, account, status in observations:
    if status != "HIT":
        continue
    if runs and runs[-1][0] == account:
        continue
    runs.append((account, t))
stretches = [round(b[1] - a[1], 1) for a, b in zip(runs, runs[1:])]

receivers = Counter()
for _, c, a, _ in observations:
    if c != a:
        receivers[a] += 1

print(
    f"clients: {args.clients}  poll interval: {args.interval}s  duration: {args.duration}s"
)
print(
    f"polls: {total}  own doors: {own}  someone else's doors: {foreign} ({foreign / total:.0%})"
)
print(f"distinct accounts handed to other clients: {len(receivers)}")
served = [a for a, _ in runs]
print(f"cache refills seen: {len(runs)}  accounts served more than once: {len(served) - len(set(served))}")
if stretches:
    print(
        "seconds each cached account was served before the next one took over: "
        f"median {statistics.median(stretches)}s, min {min(stretches)}s, max {max(stretches)}s"
    )
    print("stretch lengths:", " ".join(f"{s}s" for s in stretches))
for client in clients[:3]:
    seen = [a if a != client else "OWN" for _, c, a, _ in observations if c == client]
    compact = []
    for a in seen:
        if compact and compact[-1][0] == a:
            compact[-1][1] += 1
        else:
            compact.append([a, 1])
    print(f"{client} saw: " + ", ".join(f"{a} x{n}" for a, n in compact))
