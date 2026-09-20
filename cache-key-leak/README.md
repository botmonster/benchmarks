# Cache key leak: one user's API response served to everyone

Reproduction behind [An Aladdin Connect cache bug leaked strangers' garage doors](https://botmonster.com/smart-home/an-aladdin-connect-cache-bug-leaked-strangers-garage-doors/).

In September 2026, Home Assistant users polling Genie's Aladdin Connect cloud got other customers' garage door lists for about 18 hours. Genie said it had turned on API Gateway caching. This folder rebuilds the same class of bug on a laptop with a stock nginx cache, then fixes it two ways.

Everything installs into a local `./.tools` (nginx built from source). No sudo, no system changes, nothing listens outside `127.0.0.1`.

## What is tested

A tiny Python API ([`origin.py`](origin.py)) answers `GET /v1/devices` with a different door list for each bearer token, the way a garage door cloud would. nginx sits in front with `proxy_cache` turned on.

1. **The leak** ([`nginx/leak.conf`](nginx/leak.conf)): `proxy_cache_valid 200 300s` (the same 300 s as API Gateway's default TTL) and `proxy_cache_key` left at its default, `$scheme$proxy_host$request_uri`. Alice, Bob and Carol each ask for their own doors.
2. **Many pollers** ([`poll_sim.py`](poll_sim.py)): 40 clients poll the leaky cache about once a second for 90 s, with the TTL scaled down to 5 s. The script records which account each poll returned and how long each cached account lasted before the next one replaced it.
3. **Fix one** ([`nginx/fixed-key.conf`](nginx/fixed-key.conf)): the `Authorization` header goes into the cache key.
4. **Fix two**: the leaky config from stage 1, but the origin sends `Cache-Control: private` on per-user responses.

Stock nginx caches responses to requests that carry an `Authorization` header without complaint. It does not apply the shared-cache rule from RFC 9111 that would refuse to, so nginx needed no special setting to show the bug.

## Replicating

On Ubuntu (x86_64) with `curl`, `gcc`, `make` and `python3`:

```bash
git clone https://github.com/botmonster/benchmarks.git
cd benchmarks/cache-key-leak
./run.sh              # interactive stage gates
./run.sh --yes        # no prompts
./run.sh --latest     # newest stable nginx instead of the pinned one
```

Pinned version: nginx 1.30.4. The Python side uses only the standard library.

Files: [`run.sh`](run.sh) builds nginx and runs the four stages; [`origin.py`](origin.py) is the per-user API; [`poll_sim.py`](poll_sim.py) is the multi-client poller; [`nginx/`](nginx/) holds both configs. Raw output lands in [`results/`](results/).

## Author's results

Machine: AMD Ryzen 9 5900X, 62 GB RAM, Linux Mint 22.3 (Ubuntu 24.04 base), Python 3.12.3, nginx 1.30.4.

**Stage 1, the leak** ([`results/stage1-leak.txt`](results/stage1-leak.txt), raw headers in [`results/stage1-leak-raw.txt`](results/stage1-leak-raw.txt)):

```
alice  asks -> own doors                (X-Cache-Status: MISS)
bob    asks -> LEAK: alice's doors      (X-Cache-Status: HIT)
carol  asks -> LEAK: alice's doors      (X-Cache-Status: HIT)
alice  asks -> own doors                (X-Cache-Status: HIT)
origin log:
  11:19:06 origin answered for alice
```

**Stage 2, 40 pollers** ([`results/stage2-poll-sim.txt`](results/stage2-poll-sim.txt), every poll in [`results/poll-sim.csv`](results/poll-sim.csv)):

- 3,274 polls, 97% of them returned someone else's doors.
- 14 different accounts were handed out to the other clients in 90 s.
- Each cached account lasted 5.7 to 6.1 s (median 6.0 s): the 5 s TTL plus up to one poll interval of lag. Scaled up, that is the 300 to 314 s signature Home Assistant users measured against the Aladdin Connect API.
- The client whose poll refilled the cache saw its own doors for that whole stretch. Everyone else saw that client's doors.

**Stage 3 and 4, the fixes** ([`results/stage3-fix-key.txt`](results/stage3-fix-key.txt), [`results/stage4-fix-private.txt`](results/stage4-fix-private.txt)): every user gets their own doors. With the token in the key, Alice's second request is a cache `HIT` on her own entry. With `Cache-Control: private`, nginx stores nothing and every request goes to the origin.

## License

[MIT](../LICENSE)
