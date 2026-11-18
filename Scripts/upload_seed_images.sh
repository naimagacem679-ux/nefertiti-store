#!/usr/bin/env bash
# Uploads seed-images/* to R2 under the SAME keys that db/seed.sql references.
# Run once, after: wrangler r2 bucket create nefertiti-images   (add --remote only when you are ready)
set -e
cd "$(dirname "$0")/.."
BUCKET="${1:-nefertiti-images}"
for f in seed-images/*; do
  k="$(basename "$f")"
  case "$k" in *.jpg) ct=image/jpeg;; *.png) ct=image/png;; *.webp) ct=image/webp;; *.gif) ct=image/gif;; *) ct=application/octet-stream;; esac
  echo "put $k"; npx wrangler r2 object put "$BUCKET/$k" --file "$f" --content-type "$ct" --remote
done
