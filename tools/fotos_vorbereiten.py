#!/usr/bin/env python3
"""Bringt Fotos in Web-Größe, erzeugt Thumbs und pflegt das Manifest.

Braucht Pillow:  pip install Pillow

    # Neue Bilder von der Karte/Platte in eine Etappe übernehmen
    python3 tools/fotos_vorbereiten.py tag-07 ~/Bilder/RGA/tag07/*.jpg

    # Bilder, die schon in fotos/tag-07/ liegen, nachbearbeiten
    python3 tools/fotos_vorbereiten.py tag-07

    # Alle Etappen durchgehen (z. B. nach einer Änderung der Zielgrößen)
    python3 tools/fotos_vorbereiten.py --alle

Ergebnis je Etappe:
    fotos/tag-07/img_0421.jpg         lange Kante max 1600 px, Qualität 80
    fotos/tag-07/thumbs/img_0421.jpg  lange Kante 400 px, für das Raster

Danach steht die Dateiliste in data/reise.json unter "fotos". Titel, die dort
schon eingetragen sind, bleiben erhalten -- neue Bilder kommen mit leerem
Titel dazu, den man dann von Hand ergänzt.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow fehlt. Installieren mit:  pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
FOTOS = ROOT / "fotos"
REISE = ROOT / "data" / "reise.json"

GROSS = 1600
THUMB = 400
QUALITAET = 80
ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".HEIC"}


def sauberer_name(name: str) -> str:
    """Dateiname ohne Umlaute, Leerzeichen und Großbuchstaben -- URLs mögen das."""
    stamm = Path(name).stem.lower()
    stamm = (stamm.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))
    stamm = re.sub(r"[^a-z0-9]+", "-", stamm).strip("-") or "foto"
    return stamm + ".jpg"


def skalieren(quelle: Path, ziel: Path, kante: int):
    with Image.open(quelle) as bild:
        bild = ImageOps.exif_transpose(bild)          # gedrehte Handyfotos aufrichten
        if bild.mode not in ("RGB", "L"):
            bild = bild.convert("RGB")
        bild.thumbnail((kante, kante), Image.LANCZOS)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        bild.save(ziel, "JPEG", quality=QUALITAET, optimize=True, progressive=True)
    return ziel.stat().st_size


def etappe_verarbeiten(tag_id: str, quellen):
    ordner = FOTOS / tag_id
    thumbs = ordner / "thumbs"
    ordner.mkdir(parents=True, exist_ok=True)

    if quellen:
        for q in quellen:
            q = Path(q)
            if not q.is_file():
                print(f"  übersprungen (keine Datei): {q}")
                continue
            ziel = ordner / sauberer_name(q.name)
            groesse = skalieren(q, ziel, GROSS)
            print(f"  {q.name} → {ziel.name}  {groesse / 1024:.0f} KB")
    else:
        # Schon liegende Bilder normalisieren: umbenennen, aufrichten, verkleinern.
        for bild in sorted(ordner.iterdir()):
            if not bild.is_file() or bild.suffix not in ENDUNGEN:
                continue
            ziel = ordner / sauberer_name(bild.name)
            if ziel != bild:
                if ziel.exists():
                    print(f"  {bild.name}: {ziel.name} gibt es schon, übersprungen")
                    continue
                shutil.move(str(bild), str(ziel))
            with Image.open(ziel) as b:
                zu_gross = max(b.size) > GROSS
            if zu_gross or ziel.suffix.lower() != ".jpg":
                groesse = skalieren(ziel, ziel, GROSS)
                print(f"  {ziel.name} verkleinert  {groesse / 1024:.0f} KB")

    bilder = sorted(p for p in ordner.iterdir() if p.is_file() and p.suffix == ".jpg")
    for bild in bilder:
        thumb = thumbs / bild.name
        if not thumb.exists() or thumb.stat().st_mtime < bild.stat().st_mtime:
            groesse = skalieren(bild, thumb, THUMB)
            print(f"  thumbs/{bild.name}  {groesse / 1024:.0f} KB")

    for thumb in sorted(thumbs.glob("*.jpg")) if thumbs.exists() else []:
        if not (ordner / thumb.name).exists():
            thumb.unlink()
            print(f"  thumbs/{thumb.name} entfernt (Original weg)")

    return [b.name for b in bilder]


def manifest_pflegen(tag_id: str, dateien):
    reise = json.loads(REISE.read_text(encoding="utf-8"))
    etappe = next((x for x in reise["etappen"] if x["id"] == tag_id), None)
    if etappe is None:
        sys.exit(f"{tag_id} steht nicht in data/reise.json")

    alt = {f["datei"]: f for f in etappe.get("fotos") or []}
    neu = [alt.get(d, {"datei": d, "titel": ""}) for d in dateien]
    dazu = [d for d in dateien if d not in alt]
    weg = [d for d in alt if d not in dateien]

    etappe["fotos"] = neu
    REISE.write_text(json.dumps(reise, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"  Manifest: {len(neu)} Fotos" + (f", neu: {', '.join(dazu)}" if dazu else "")
          + (f", entfernt: {', '.join(weg)}" if weg else ""))
    ohne_titel = [f["datei"] for f in neu if not f["titel"]]
    if ohne_titel:
        print(f"  noch ohne Titel: {', '.join(ohne_titel)}")


def main():
    ap = argparse.ArgumentParser(description="Fotos skalieren, Thumbs bauen, Manifest pflegen.")
    ap.add_argument("tag", nargs="?", help="Etappe, z. B. tag-07")
    ap.add_argument("quellen", nargs="*", help="Bilddateien, die übernommen werden sollen")
    ap.add_argument("--alle", action="store_true", help="alle Etappen aus data/reise.json durchgehen")
    args = ap.parse_args()

    if args.alle:
        reise = json.loads(REISE.read_text(encoding="utf-8"))
        tage = [x["id"] for x in reise["etappen"]]
    elif args.tag:
        tage = [args.tag]
    else:
        ap.error("entweder eine Etappe angeben oder --alle")

    for tag_id in tage:
        if not re.fullmatch(r"tag-\d{2}", tag_id):
            sys.exit(f"'{tag_id}' sieht nicht wie 'tag-07' aus")
        if args.alle and not (FOTOS / tag_id).is_dir():
            continue
        print(f"{tag_id}:")
        dateien = etappe_verarbeiten(tag_id, args.quellen if not args.alle else [])
        manifest_pflegen(tag_id, dateien)
        if not dateien:
            print("  keine Bilder gefunden")


if __name__ == "__main__":
    main()
