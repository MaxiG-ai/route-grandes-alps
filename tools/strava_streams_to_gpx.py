#!/usr/bin/env python3
"""Turns Strava activity streams into gpx/day-NN.gpx.

    python3 tools/strava_streams_to_gpx.py day-12 streams/tag12.json
    python3 tools/strava_streams_to_gpx.py day-07 part1.json part2.json

Each input file is the JSON the Strava stream API returns for one activity,
i.e. an object with a "location" array of [lat, lon] pairs and an "altitude"
array of metres:

    {"location": [[45.62, 6.80], …], "altitude": [1050.2, …]}

Several files are concatenated in the order given, which is how a stage
recorded as two activities becomes one track.

Waypoints already present in the target GPX are carried over, so the
komoot markers survive a track being replaced.

Note on resolution: streams fetched through the API are resampled, so the
distance and climbing derived from them come out slightly below what Strava
reports. The original "Export GPX" file from an activity page is better
still — drop it in as gpx/day-NN.gpx and rebuild, nothing else changes.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
GPX_DIR = ROOT / "gpx"


def existing_waypoints(path):
    """Keep the <wpt> entries of a GPX file we are about to overwrite."""
    if not path.exists():
        return []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    root = tree.getroot()
    ns = {"g": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {"g": ""}
    kept = []
    for wpt in tree.iterfind(".//g:wpt", ns):
        name = wpt.find("g:name", ns)
        kept.append((wpt.get("lat"), wpt.get("lon"),
                     (name.text or "").strip() if name is not None else "Wegpunkt"))
    return kept


def read_streams(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    location = data.get("location") or []
    altitude = data.get("altitude") or []
    if not location:
        sys.exit(f"{path}: no 'location' stream")
    if len(altitude) != len(location):
        sys.exit(f"{path}: {len(location)} locations but {len(altitude)} altitudes")
    return list(zip(location, altitude))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    stage_id, sources = sys.argv[1], sys.argv[2:]
    if not re.fullmatch(r"day-\d{2}", stage_id):
        sys.exit(f"'{stage_id}' does not look like 'day-07'")

    points = []
    for source in sources:
        points.extend(read_streams(source))

    target = GPX_DIR / f"{stage_id}.gpx"
    waypoints = existing_waypoints(target)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="tools/strava_streams_to_gpx.py"',
        '     xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <metadata><name>{escape(stage_id)}</name></metadata>",
    ]
    for lat, lon, name in waypoints:
        lines.append(f'  <wpt lat="{lat}" lon="{lon}"><name>{escape(name)}</name></wpt>')
    lines.append("  <trk>")
    lines.append(f"    <name>{escape(stage_id)}</name>")
    lines.append("    <trkseg>")
    for (lat, lon), ele in points:
        lines.append(f'      <trkpt lat="{lat}" lon="{lon}"><ele>{ele}</ele></trkpt>')
    lines.append("    </trkseg>")
    lines.append("  </trk>")
    lines.append("</gpx>")

    GPX_DIR.mkdir(exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(points)} points from {len(sources)} "
          f"activit{'y' if len(sources) == 1 else 'ies'}, "
          f"{len(waypoints)} waypoints kept, {target.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
