#!/usr/bin/env bash
# Proves the backup is intact and that the working copy of the store page is still byte-identical to it.
set -e
cd "$(dirname "$0")/.."
( cd db/source && sha256sum -c SHA256SUMS.txt )
cmp db/source/index.original.html public/index.html && echo "public/index.html is byte-identical to the original backup (phase 1 changes nothing in the store)."
