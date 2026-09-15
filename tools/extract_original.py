#!/usr/bin/env python3
"""One-off migration out of the original single-file prototype.

    python3 tools/extract_original.py

Reads reference/index-original.html and writes:
    gpx/day-01.gpx … gpx/day-14.gpx   track and waypoints per stage
    data/trip.json                    hand-written stage content

The prototype carried its tracks as already-thinned JSON (310-800 points a
stage), so the GPX files this writes are lower resolution than a fresh
komoot or Strava export. Distance and climbing therefore come out about a
percent below the numbers the prototype showed. Dropping the real exports
into gpx/ and rebuilding fixes that.

Careful: data/trip.json is overwritten wholesale. Once lodging, summaries
or photos are written into it, do not run this again.
"""
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "reference" / "index-original.html"
GPX_DIR = ROOT / "gpx"
DATA = ROOT / "data"

# The German wording for the three gaps in the recorded tracks. The prototype
# had these in English; the site is German, so they are translated here.
GAP_TEXT = {
    "day3": "13 km Transfer sind nicht im Track",
    "day5": "Fähre über den Genfer See, 13 km",
    "day12": "Nach Regen umgeplant: Tag 11 endete in Pra Loup, 20 km vor Les Pommiers",
}


def js_const(source, name):
    """Read `const NAME = <json>;` out of the prototype's script block."""
    found = re.search(r"^const %s = (.*);\s*$" % name, source, re.MULTILINE)
    if not found:
        sys.exit(f"'const {name}' not found in {SOURCE.name}")
    return json.loads(found.group(1))


def stage_id(old):
    return "day-%02d" % int(old.replace("day", ""))


def write_gpx(path, name, points, waypoints):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="tools/extract_original.py"',
        '     xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <metadata><name>{escape(name)}</name></metadata>",
    ]
    for w in waypoints:
        lines.append(f'  <wpt lat="{w["lat"]}" lon="{w["lon"]}">'
                     f'<name>{escape(w["name"])}</name></wpt>')
    lines.append("  <trk>")
    lines.append(f"    <name>{escape(name)}</name>")
    lines.append("    <trkseg>")
    for p in points:
        lines.append(f'      <trkpt lat="{p["lat"]}" lon="{p["lon"]}">'
                     f'<ele>{p["ele"]}</ele></trkpt>')
    lines.append("    </trkseg>")
    lines.append("  </trk>")
    lines.append("</gpx>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    source = SOURCE.read_text(encoding="utf-8")
    routes = js_const(source, "ROUTES")
    passes = js_const(source, "PASSES")
    quaeldich = re.search(r'^const QD_PROFILE = "([^"]+)"', source, re.MULTILINE)

    GPX_DIR.mkdir(exist_ok=True)
    stages = []

    for no, route in enumerate(routes, start=1):
        sid = stage_id(route["id"])
        if " → " not in route["displayName"]:
            sys.exit(f"{sid}: displayName without ' → ': {route['displayName']!r}")
        start, end = route["displayName"].split(" → ", 1)

        write_gpx(GPX_DIR / f"{sid}.gpx", f"Tag {no}: {start} → {end}",
                  route["points"], route["waypoints"])

        stages.append({
            "id": sid,
            "no": no,
            "from": start,
            "to": end,
            "date": route["date"],
            "gap": GAP_TEXT.get(route["id"]),
            "plannedPasses": route["cols"],
            "passes": [
                {"name": p["name"], "eleM": p["ele"], "url": p.get("url"),
                 "manual": bool(p.get("manual"))}
                for p in passes.get(route["id"], [])
            ],
            "strava": [{"id": a["id"], "name": a["name"]} for a in route["strava"]],
            # Everything below is hand-written; empty fields are left out of the page.
            "lodging": None,
            "summary": [],
            "photos": [],
        })
        print(f'  {sid}.gpx  {len(route["points"]):4} points, '
              f'{len(route["waypoints"]):2} waypoints, was {route["distanceKm"]} km')

    trip = {
        "title": "Rhein bis Riviera",
        "subtitle": "Bikepacking auf der Route des Grandes Alpes",
        "stravaProfile": "https://www.strava.com/athletes/11965636",
        "quaeldichProfile": quaeldich.group(1) if quaeldich else None,
        "coverPhoto": None,
        "stages": stages,
    }
    (DATA / "trip.json").write_text(
        json.dumps(trip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n  data/trip.json  {(DATA / 'trip.json').stat().st_size / 1024:.0f} KB, "
          f"{len(stages)} stages")
    print("\nNext:  python3 tools/build.py")


if __name__ == "__main__":
    main()
