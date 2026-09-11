#!/usr/bin/env python3
"""Shared GPX parsing: read a file, derive stats, thin the geometry.

Used by tools/build.py. Stats are computed on the full-resolution track;
only the geometry that ships to the browser gets thinned.
"""
import math
import xml.etree.ElementTree as ET
from pathlib import Path

MIN_POINT_SPACING_M = 12    # points closer than this are dropped from the output
MAX_TRACK_POINTS = 1200     # hard cap per stage, keeps the JSON small
MAX_OVERVIEW_POINTS = 90    # per stage, for the map on the landing page
PROFILE_SAMPLES = 48        # per stage, for the sparklines
SMOOTHING_WINDOW = 5        # moving average over elevation, in points
CLIMB_THRESHOLD_M = 1.0     # ignore elevation wobble below this


class GpxError(Exception):
    pass


def distance_km(a, b):
    """Haversine distance between (lat, lon) pairs, in kilometres."""
    r = 6371.0088
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def read(path):
    """Parse a GPX file into (points, waypoints).

    Points are dicts with lat/lon/ele at full resolution, in file order.
    Track segments are concatenated -- a stage is one ride even if the
    recording was split. Falls back to <rtept> for route-style exports.
    """
    path = Path(path)
    try:
        tree = ET.parse(path)
    except ET.ParseError as err:
        raise GpxError(f"{path.name}: not valid XML ({err})") from err

    root = tree.getroot()
    if "}" in root.tag:
        ns = {"g": root.tag.split("}")[0].strip("{")}
    else:
        ns = {"g": ""}

    # <trkpt> is what a recorded track and komoot's "GPX Track" export use;
    # komoot's "GPX Route" export writes <rtept> instead, so accept both.
    points = []
    for tag in ("trkpt", "rtept"):
        for pt in tree.iterfind(f".//g:{tag}", ns):
            ele = pt.find("g:ele", ns)
            try:
                points.append({
                    "lat": float(pt.get("lat")),
                    "lon": float(pt.get("lon")),
                    "ele": float(ele.text) if ele is not None and ele.text else None,
                })
            except (TypeError, ValueError) as err:
                raise GpxError(f"{path.name}: unreadable <{tag}> ({err})") from err
        if points:
            break

    if not points:
        raise GpxError(f"{path.name}: no <trkpt> or <rtept> found -- is the file empty?")

    missing_ele = sum(1 for p in points if p["ele"] is None)
    if missing_ele == len(points):
        raise GpxError(f"{path.name}: no <ele> values, so there is no elevation profile")
    if missing_ele:
        # Fill gaps with the previous known value; better than dropping the point.
        last = next(p["ele"] for p in points if p["ele"] is not None)
        for p in points:
            if p["ele"] is None:
                p["ele"] = last
            else:
                last = p["ele"]

    waypoints = []
    for wpt in tree.iterfind(".//g:wpt", ns):
        name = wpt.find("g:name", ns)
        waypoints.append({
            "lat": round(float(wpt.get("lat")), 6),
            "lon": round(float(wpt.get("lon")), 6),
            "name": (name.text or "").strip() if name is not None else "Wegpunkt",
        })

    return points, waypoints


def smooth_elevation(points, window=SMOOTHING_WINDOW):
    """Moving average over elevation. Raw GPS elevation is noisy enough to
    invent a few hundred metres of climbing over a long stage."""
    if window <= 1 or len(points) < window:
        return [p["ele"] for p in points]
    eles = [p["ele"] for p in points]
    half = window // 2
    return [sum(eles[max(0, i - half):i + half + 1]) / len(eles[max(0, i - half):i + half + 1])
            for i in range(len(eles))]


def climb(eles, threshold=CLIMB_THRESHOLD_M):
    """Total ascent and descent, ignoring wobble below the threshold."""
    up = down = 0.0
    reference = eles[0]
    for ele in eles[1:]:
        delta = ele - reference
        if abs(delta) < threshold:
            continue
        if delta > 0:
            up += delta
        else:
            down -= delta
        reference = ele
    return up, down


def thin(points, min_spacing_m=MIN_POINT_SPACING_M, cap=MAX_TRACK_POINTS):
    """Drop points closer together than min_spacing_m, then cap the count.
    Keeps first and last point either way."""
    kept = [points[0]]
    for p in points[1:-1]:
        if distance_km((kept[-1]["lat"], kept[-1]["lon"]), (p["lat"], p["lon"])) * 1000 >= min_spacing_m:
            kept.append(p)
    kept.append(points[-1])
    if len(kept) > cap:
        kept = every_nth(kept, cap)
    return kept


def every_nth(points, maximum):
    """Evenly spaced subset, first and last point kept."""
    if len(points) <= maximum:
        return list(points)
    step = len(points) / maximum
    picked = [points[int(i * step)] for i in range(maximum)]
    if picked[-1] is not points[-1]:
        picked.append(points[-1])
    return picked


def profile_samples(points, count=PROFILE_SAMPLES):
    """Elevation at evenly spaced distances -- the data behind the sparklines."""
    total = points[-1]["d"]
    values, i = [], 0
    for k in range(count):
        target = total * k / (count - 1)
        while i + 1 < len(points) and points[i + 1]["d"] <= target:
            i += 1
        values.append(round(points[i]["ele"]))
    return values


def parse(path, smoothing=SMOOTHING_WINDOW):
    """Full pipeline for one stage.

    Returns a dict with the numbers for the page plus the thinned geometry
    for data/tracks/<id>.json. Distance and climbing come from the
    full-resolution track, so thinning does not eat away at them.
    """
    raw, waypoints = read(path)
    eles = smooth_elevation(raw, smoothing)
    for p, ele in zip(raw, eles):
        p["ele"] = round(ele, 1)

    total_km = 0.0
    for before, after in zip(raw, raw[1:]):
        total_km += distance_km((before["lat"], before["lon"]), (after["lat"], after["lon"]))
    up, down = climb([p["ele"] for p in raw])

    points = thin(raw)
    walked = 0.0
    points[0] = dict(points[0], d=0.0)
    for i in range(1, len(points)):
        walked += distance_km((points[i - 1]["lat"], points[i - 1]["lon"]),
                              (points[i]["lat"], points[i]["lon"]))
        points[i] = dict(points[i], d=round(walked, 3))
    # Stretch the thinned distances onto the full-resolution total, so the
    # profile axis and the headline distance agree.
    if walked > 0:
        scale = total_km / walked
        for p in points:
            p["d"] = round(p["d"] * scale, 3)

    all_ele = [p["ele"] for p in raw]
    return {
        "rawPoints": len(raw),
        "points": [{"lat": round(p["lat"], 5), "lon": round(p["lon"], 5),
                    "ele": p["ele"], "d": p["d"]} for p in points],
        "waypoints": waypoints,
        "distanceKm": round(total_km, 1),
        "ascentM": round(up),
        "descentM": round(down),
        "minEleM": round(min(all_ele)),
        "maxEleM": round(max(all_ele)),
        "profile": profile_samples(points),
        "start": [round(raw[0]["lat"], 6), round(raw[0]["lon"], 6)],
        "end": [round(raw[-1]["lat"], 6), round(raw[-1]["lon"], 6)],
    }
