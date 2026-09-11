#!/usr/bin/env python3
"""Resize photos for the web, build thumbnails, keep the manifest in sync.

Needs Pillow:  pip install Pillow

    # take new images from a card or disk into one stage
    python3 tools/prepare_photos.py day-07 ~/Pictures/RGA/day07/*.jpg

    # rework images that already sit in photos/day-07/
    python3 tools/prepare_photos.py day-07

    # walk every stage (after changing the target sizes, say)
    python3 tools/prepare_photos.py --all

Per stage this writes:
    photos/day-07/img-0421.jpg         long edge max 1600 px, quality 80
    photos/day-07/thumbs/img-0421.jpg  long edge 400 px, for the grid

Afterwards the file list sits in data/trip.json under "photos". Captions
already written there are kept -- new images arrive with an empty caption
to fill in by hand.
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
    sys.exit("Pillow is missing. Install it with:  pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "photos"
TRIP = ROOT / "data" / "trip.json"

FULL_EDGE = 1600
THUMB_EDGE = 400
QUALITY = 80
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".HEIC"}


def web_name(name):
    """Filename without umlauts, spaces or capitals -- URLs prefer that."""
    stem = Path(name).stem.lower()
    stem = stem.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "photo"
    return stem + ".jpg"


def resize(source, target, edge):
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)      # straighten rotated phone shots
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.thumbnail((edge, edge), Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return target.stat().st_size


def process_stage(stage_id, sources):
    folder = PHOTOS / stage_id
    thumbs = folder / "thumbs"
    folder.mkdir(parents=True, exist_ok=True)

    if sources:
        for source in sources:
            source = Path(source)
            if not source.is_file():
                print(f"  skipped (not a file): {source}")
                continue
            target = folder / web_name(source.name)
            size = resize(source, target, FULL_EDGE)
            print(f"  {source.name} → {target.name}  {size / 1024:.0f} KB")
    else:
        # Normalise images already in place: rename, straighten, shrink.
        for image in sorted(folder.iterdir()):
            if not image.is_file() or image.suffix not in SUFFIXES:
                continue
            target = folder / web_name(image.name)
            if target != image:
                if target.exists():
                    print(f"  {image.name}: {target.name} already exists, skipped")
                    continue
                shutil.move(str(image), str(target))
            with Image.open(target) as probe:
                too_big = max(probe.size) > FULL_EDGE
            if too_big or target.suffix.lower() != ".jpg":
                size = resize(target, target, FULL_EDGE)
                print(f"  {target.name} shrunk  {size / 1024:.0f} KB")

    images = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == ".jpg")
    for image in images:
        thumb = thumbs / image.name
        if not thumb.exists() or thumb.stat().st_mtime < image.stat().st_mtime:
            size = resize(image, thumb, THUMB_EDGE)
            print(f"  thumbs/{image.name}  {size / 1024:.0f} KB")

    if thumbs.exists():
        for thumb in sorted(thumbs.glob("*.jpg")):
            if not (folder / thumb.name).exists():
                thumb.unlink()
                print(f"  thumbs/{thumb.name} removed (original gone)")

    return [image.name for image in images]


def update_manifest(stage_id, files):
    trip = json.loads(TRIP.read_text(encoding="utf-8"))
    stage = next((s for s in trip["stages"] if s["id"] == stage_id), None)
    if stage is None:
        sys.exit(f"{stage_id} is not listed in data/trip.json")

    known = {p["file"]: p for p in stage.get("photos") or []}
    updated = [known.get(f, {"file": f, "caption": ""}) for f in files]
    added = [f for f in files if f not in known]
    removed = [f for f in known if f not in files]

    stage["photos"] = updated
    TRIP.write_text(json.dumps(trip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"  manifest: {len(updated)} photos"
          + (f", added: {', '.join(added)}" if added else "")
          + (f", removed: {', '.join(removed)}" if removed else ""))
    without_caption = [p["file"] for p in updated if not p["caption"]]
    if without_caption:
        print(f"  still without a caption: {', '.join(without_caption)}")


def main():
    parser = argparse.ArgumentParser(description="Resize photos, build thumbs, sync the manifest.")
    parser.add_argument("stage", nargs="?", help="stage id, e.g. day-07")
    parser.add_argument("sources", nargs="*", help="image files to take in")
    parser.add_argument("--all", action="store_true", help="walk every stage in data/trip.json")
    args = parser.parse_args()

    if args.all:
        trip = json.loads(TRIP.read_text(encoding="utf-8"))
        ids = [s["id"] for s in trip["stages"]]
    elif args.stage:
        ids = [args.stage]
    else:
        parser.error("name a stage or pass --all")

    for stage_id in ids:
        if not re.fullmatch(r"day-\d{2}", stage_id):
            sys.exit(f"'{stage_id}' does not look like 'day-07'")
        if args.all and not (PHOTOS / stage_id).is_dir():
            continue
        print(f"{stage_id}:")
        files = process_stage(stage_id, args.sources if not args.all else [])
        update_manifest(stage_id, files)
        if not files:
            print("  no images found")
    print("\nNext:  python3 tools/build.py")


if __name__ == "__main__":
    main()
