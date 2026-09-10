#!/usr/bin/env bash
# Lädt die Website ins Hetzner Webhosting. Zugangsdaten kommen aus der
# Umgebung -- niemals ins Repo schreiben.
#
#   export RGA_HOST=wXXXXXX.kasserver.com     # oder ssh-Host aus KonsoleH
#   export RGA_USER=uXXXXXX
#   export RGA_PFAD=/public_html              # Zielordner auf dem Server
#   ./tools/upload.sh                          # überträgt alles Nötige
#   ./tools/upload.sh --trocken                # zeigt nur, was passieren würde
#
# Übertragen werden genau die Dateien, die die Website braucht. tools/,
# templates/, docs/, reference/ und .git bleiben lokal.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${RGA_HOST:?RGA_HOST ist nicht gesetzt}"
: "${RGA_USER:?RGA_USER ist nicht gesetzt}"
PFAD="${RGA_PFAD:-/public_html}"

TROCKEN=()
if [[ "${1:-}" == "--trocken" ]]; then TROCKEN=(--dry-run); echo "== Trockenlauf =="; fi

# Sicherheitsnetz: veraltete Seiten würden sonst mit hochgehen.
python3 tools/build.py --check

INHALT=(index.html etappen.html packliste.html assets data fotos .htaccess)
while IFS= read -r seite; do INHALT+=("$seite"); done < <(ls tag-*.html)

echo "== Upload nach ${RGA_USER}@${RGA_HOST}:${PFAD} =="
rsync -avz --delete "${TROCKEN[@]}" \
  --exclude '.DS_Store' --exclude 'README.md' \
  "${INHALT[@]}" "${RGA_USER}@${RGA_HOST}:${PFAD}/"

echo "== Fertig. Zur Kontrolle eine Etappenseite direkt aufrufen, z. B. .../tag-07.html =="
