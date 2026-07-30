#!/usr/bin/env bash
# EclipsBox — reconstruct binary assets from their committed *.b64 text copies.
# The source was imported through a channel that cannot carry binary git blobs,
# so every binary asset (PNG icons/backgrounds, *.jar, native raw/temp,
# gradle-wrapper.jar) is stored next to its real path as <file>.b64.
# Run ONCE after cloning, before building:
#     bash tools/restore_binaries.sh
set -e
cd "$(dirname "$0")/.."
count=0
while IFS= read -r -d '' f; do
  out="${f%.b64}"
  mkdir -p "$(dirname "$out")"
  base64 -d "$f" > "$out" 2>/dev/null || base64 --decode "$f" > "$out"
  count=$((count+1))
done < <(find . -name '*.b64' -print0)
echo "restored $count binary asset(s). Safe to build now."
echo "Optional cleanup: find . -name '*.b64' -delete"
