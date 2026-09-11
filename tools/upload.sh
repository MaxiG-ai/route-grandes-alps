#!/usr/bin/env bash
# Uploads the site to the Hetzner web hosting. Credentials come from the
# environment -- never put them in the repo.
#
#   export RGA_HOST=wXXXXXX.kasserver.com     # or the SSH host from KonsoleH
#   export RGA_USER=uXXXXXX
#   export RGA_PATH=/public_html              # target directory on the server
#   ./tools/upload.sh                          # transfer everything needed
#   ./tools/upload.sh --dry-run                # show what would happen
#
# Only the files the site needs go up. tools/, templates/, docs/, gpx/,
# reference/ and .git stay local.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${RGA_HOST:?RGA_HOST is not set}"
: "${RGA_USER:?RGA_USER is not set}"
TARGET_PATH="${RGA_PATH:-/public_html}"

DRY_RUN=()
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=(--dry-run)
  echo "== dry run =="
fi

# Safety net: stale pages would otherwise go up with everything else.
python3 tools/build.py --check

CONTENT=(index.html stages.html packing-list.html assets data photos .htaccess)
while IFS= read -r stage_page; do CONTENT+=("$stage_page"); done < <(ls day-*.html)

echo "== uploading to ${RGA_USER}@${RGA_HOST}:${TARGET_PATH} =="
rsync -avz --delete "${DRY_RUN[@]}" \
  --exclude '.DS_Store' --exclude 'README.md' \
  "${CONTENT[@]}" "${RGA_USER}@${RGA_HOST}:${TARGET_PATH}/"

echo "== done. Open a stage page directly to check, e.g. .../day-07.html =="
