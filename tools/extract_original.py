#!/usr/bin/env python3
"""Zieht die Daten aus der ursprünglichen Einzeldatei in die Struktur unter data/.

Einmal-Migration, aber reproduzierbar: Quelle ist reference/index-original.html,
Ziel sind data/reise.json (handgepflegt weiterzuführen), data/tracks/tag-NN.json
(maschinenerzeugt) und data/uebersicht.json.

    python3 tools/extract_original.py

Achtung: data/reise.json wird dabei überschrieben. Sobald dort Übernachtungen,
Zusammenfassungen und Fotos eingetragen sind, dieses Skript nicht mehr laufen
lassen -- ab dann pflegt tools/gpx_to_track.py nur noch die Tracks.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reference" / "index-original.html"
DATA = ROOT / "data"

MAX_UEBERSICHT_PUNKTE = 90    # je Etappe, für die Übersichtskarte
PROFIL_STUETZEN = 48          # je Etappe, für die Sparklines


def js_const(quelle: str, name: str):
    """Liest `const NAME = <json>;` aus dem Skriptblock der Originaldatei."""
    treffer = re.search(r"^const %s = (.*);\s*$" % name, quelle, re.MULTILINE)
    if not treffer:
        sys.exit(f"'const {name}' nicht gefunden in {SRC.name}")
    return json.loads(treffer.group(1))


def tag_id(alt: str) -> str:
    return "tag-%02d" % int(alt.replace("day", ""))


def ausduennen(punkte, maximum):
    if len(punkte) <= maximum:
        return list(punkte)
    schritt = len(punkte) / maximum
    gewaehlt = [punkte[int(i * schritt)] for i in range(maximum)]
    if gewaehlt[-1] is not punkte[-1]:
        gewaehlt.append(punkte[-1])
    return gewaehlt


def profil_stuetzen(punkte, anzahl):
    """Höhenwerte in gleichmäßigen Distanzschritten -- Basis der Sparklines."""
    gesamt = punkte[-1]["d"]
    werte, index = [], 0
    for i in range(anzahl):
        ziel = gesamt * i / (anzahl - 1)
        while index + 1 < len(punkte) and punkte[index + 1]["d"] <= ziel:
            index += 1
        werte.append(round(punkte[index]["ele"]))
    return werte


def main():
    quelle = SRC.read_text(encoding="utf-8")
    routes = js_const(quelle, "ROUTES")
    passes = js_const(quelle, "PASSES")
    gaps = js_const(quelle, "GAPS")
    qd = re.search(r'^const QD_PROFILE = "([^"]+)"', quelle, re.MULTILINE)

    (DATA / "tracks").mkdir(parents=True, exist_ok=True)
    etappen, uebersicht = [], []

    for nr, route in enumerate(routes, start=1):
        tid = tag_id(route["id"])
        if " → " not in route["displayName"]:
            sys.exit(f"{tid}: displayName ohne ' → ': {route['displayName']!r}")
        von, nach = route["displayName"].split(" → ", 1)
        punkte = route["points"]

        etappen.append({
            "id": tid,
            "nr": nr,
            "von": von,
            "nach": nach,
            "datum": route["date"],
            "distanzKm": route["distanceKm"],
            "aufstiegM": round(route["elevGainM"]),
            "abstiegM": round(route["elevLossM"]),
            "minHoehe": round(route["minEle"]),
            "maxHoehe": round(route["maxEle"]),
            "luecke": gaps.get(route["id"]),
            "geplant": route["cols"],
            "paesse": [
                {
                    "name": p["name"],
                    "hoehe": p["ele"],
                    "url": p.get("url"),
                    "manuell": bool(p.get("manual")),
                }
                for p in passes.get(route["id"], [])
            ],
            "strava": [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "distanzKm": a["dist"],
                    "aufstiegM": round(a["gain"]),
                }
                for a in route["strava"]
            ],
            "profil": profil_stuetzen(punkte, PROFIL_STUETZEN),
            "start": [route["startLat"], route["startLon"]],
            "ziel": [route["endLat"], route["endLon"]],
            # Ab hier Handarbeit -- leere Felder lässt die Seite einfach weg.
            "uebernachtung": None,
            "zusammenfassung": [],
            "fotos": [],
        })

        track = {
            "id": tid,
            "punkte": [
                {"lat": p["lat"], "lon": p["lon"], "ele": p["ele"], "d": p["d"]}
                for p in punkte
            ],
            "wegpunkte": [
                {"lat": w["lat"], "lon": w["lon"], "name": w["name"]}
                for w in route["waypoints"]
            ],
        }
        ziel = DATA / "tracks" / f"{tid}.json"
        ziel.write_text(
            json.dumps(track, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        uebersicht.append({
            "id": tid,
            "nr": nr,
            "punkte": [
                [round(p["lat"], 5), round(p["lon"], 5)]
                for p in ausduennen(punkte, MAX_UEBERSICHT_PUNKTE)
            ],
        })
        print(f"  {tid}  {len(punkte):4} Punkte  ->  {ziel.relative_to(ROOT)} "
              f"({ziel.stat().st_size / 1024:.0f} KB)")

    reise = {
        "titel": "Rhein bis Riviera",
        "untertitel": "Bikepacking auf der Route des Grandes Alpes",
        "start": etappen[0]["von"],
        "ziel": etappen[-1]["nach"],
        "von": etappen[0]["datum"],
        "bis": etappen[-1]["datum"],
        "stravaProfil": "https://www.strava.com/athletes/11965636",
        "quaeldichProfil": qd.group(1) if qd else None,
        "titelbild": None,
        "etappen": etappen,
    }
    (DATA / "reise.json").write_text(
        json.dumps(reise, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA / "uebersicht.json").write_text(
        json.dumps(uebersicht, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")

    def kb(p):
        return f"{p.stat().st_size / 1024:.0f} KB"

    print(f"\n  data/reise.json      {kb(DATA / 'reise.json')}")
    print(f"  data/uebersicht.json {kb(DATA / 'uebersicht.json')}")


if __name__ == "__main__":
    main()
