#!/usr/bin/env bash
# Re-downloads the ten test pages listed in sources.tsv and rewrites each
# fixture's page.html and meta.json. The benchmark does not need this: the
# fixtures are committed. Run it only to refresh the corpus or to check
# provenance. Probes are written against the committed HTML, so a refresh may
# require updating probes.yaml.
set -euo pipefail
export LC_ALL=C.UTF-8
cd "$(dirname "$0")"

FETCHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

while IFS=$'\t' read -r slug url license license_url attribution; do
  [ -n "$slug" ] || continue
  mkdir -p "pages/$slug"
  printf 'fetching %-34s %s\n' "$slug" "$url"
  curl -sSL --compressed --retry 3 --retry-delay 2 -o "pages/$slug/page.html" "$url"
  bytes=$(stat -c%s "pages/$slug/page.html")
  python3 - "$slug" "$url" "$license" "$license_url" "$attribution" "$FETCHED_AT" "$bytes" <<'PY'
import json, sys
slug, url, lic, lic_url, attribution, fetched_at, size = sys.argv[1:8]
meta = {
    "slug": slug,
    "source_url": url,
    "license": lic,
    "license_url": lic_url,
    "attribution": attribution,
    "fetched_at": fetched_at,
    "bytes": int(size),
}
with open(f"pages/{slug}/meta.json", "w") as fh:
    json.dump(meta, fh, indent=2)
    fh.write("\n")
PY
done < sources.tsv

echo "done. ten fixtures under pages/"
