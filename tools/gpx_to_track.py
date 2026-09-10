#!/usr/bin/env python3
"""GPX-Datei → data/tracks/<tag>.json, plus Kennzahlen für data/reise.json.

    python3 tools/gpx_to_track.py tag-15 ~/Downloads/etappe15.gpx

Erzeugt data/tracks/tag-15.json (Punkte mit lat/lon/ele/d und Wegpunkte),
aktualisiert data/uebersicht.json und schreibt Distanz, Auf- und Abstieg,
Höhenwerte, Start-/Zielkoordinaten und die Profil-Stützpunkte in den
passenden Etappen-Eintrag von data/reise.json. Handgeschriebene Felder
(von, nach, datum, uebernachtung, zusammenfassung, fotos, paesse) bleiben
unangetastet; fehlt die Etappe, wird ein Gerüst mit leeren Feldern angelegt.

    --datum 2026-09-13   Datum für eine neu angelegte Etappe
    --von / --nach       Ortsnamen für eine neu angelegte Etappe
    --glaetten 3         Höhenwerte über N Punkte mitteln (Vorgabe 3), 1 = aus
"""
import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAX_UEBERSICHT_PUNKTE = 90
PROFIL_STUETZEN = 48
MIN_ABSTAND_M = 12          # Punkte dichter als das werden verworfen
STEIGUNG_SCHWELLE_M = 1.0   # kleinere Höhenzuckungen zählen nicht als Anstieg


def entfernung(a, b):
    """Haversine in Kilometern."""
    r = 6371.0088
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def gpx_lesen(pfad):
    baum = ET.parse(pfad)
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    if not baum.getroot().tag.startswith("{http://www.topografix.com/GPX/1/1}"):
        ns = {"g": baum.getroot().tag.split("}")[0].strip("{")}

    punkte = []
    for p in baum.iterfind(".//g:trkpt", ns):
        ele = p.find("g:ele", ns)
        punkte.append({
            "lat": round(float(p.get("lat")), 5),
            "lon": round(float(p.get("lon")), 5),
            "ele": round(float(ele.text), 1) if ele is not None else 0.0,
        })
    wegpunkte = []
    for w in baum.iterfind(".//g:wpt", ns):
        name = w.find("g:name", ns)
        wegpunkte.append({
            "lat": round(float(w.get("lat")), 6),
            "lon": round(float(w.get("lon")), 6),
            "name": (name.text or "").strip() if name is not None else "Wegpunkt",
        })
    if not punkte:
        sys.exit(f"{pfad}: keine <trkpt> gefunden")
    return punkte, wegpunkte


def ausduennen_nach_abstand(punkte, min_m):
    behalten = [punkte[0]]
    for p in punkte[1:-1]:
        if entfernung((behalten[-1]["lat"], behalten[-1]["lon"]), (p["lat"], p["lon"])) * 1000 >= min_m:
            behalten.append(p)
    behalten.append(punkte[-1])
    return behalten


def glaetten(punkte, fenster):
    if fenster <= 1:
        return punkte
    werte = [p["ele"] for p in punkte]
    halb = fenster // 2
    for i, p in enumerate(punkte):
        teil = werte[max(0, i - halb):i + halb + 1]
        p["ele"] = round(sum(teil) / len(teil), 1)
    return punkte


def distanzen_setzen(punkte):
    d = 0.0
    punkte[0]["d"] = 0.0
    for vor, p in zip(punkte, punkte[1:]):
        d += entfernung((vor["lat"], vor["lon"]), (p["lat"], p["lon"]))
        p["d"] = round(d, 3)
    return d


def hoehenmeter(punkte):
    auf = ab = 0.0
    referenz = punkte[0]["ele"]
    for p in punkte[1:]:
        diff = p["ele"] - referenz
        if abs(diff) < STEIGUNG_SCHWELLE_M:
            continue
        if diff > 0:
            auf += diff
        else:
            ab -= diff
        referenz = p["ele"]
    return auf, ab


def profil_stuetzen(punkte, anzahl):
    gesamt = punkte[-1]["d"]
    werte, i = [], 0
    for k in range(anzahl):
        ziel = gesamt * k / (anzahl - 1)
        while i + 1 < len(punkte) and punkte[i + 1]["d"] <= ziel:
            i += 1
        werte.append(round(punkte[i]["ele"]))
    return werte


def gleichmaessig(punkte, maximum):
    if len(punkte) <= maximum:
        return list(punkte)
    schritt = len(punkte) / maximum
    gewaehlt = [punkte[int(i * schritt)] for i in range(maximum)]
    if gewaehlt[-1] is not punkte[-1]:
        gewaehlt.append(punkte[-1])
    return gewaehlt


def main():
    ap = argparse.ArgumentParser(description="GPX in Track- und Etappendaten übersetzen.")
    ap.add_argument("tag", help="Etappen-Id, z. B. tag-15")
    ap.add_argument("gpx", help="GPX-Datei")
    ap.add_argument("--datum", help="Datum (JJJJ-MM-TT) für eine neue Etappe")
    ap.add_argument("--von", help="Startort für eine neue Etappe")
    ap.add_argument("--nach", help="Zielort für eine neue Etappe")
    ap.add_argument("--glaetten", type=int, default=3, metavar="N",
                    help="Höhenwerte über N Punkte mitteln (Vorgabe 3, 1 = aus)")
    args = ap.parse_args()

    if not re.fullmatch(r"tag-\d{2}", args.tag):
        sys.exit(f"'{args.tag}' sieht nicht wie 'tag-07' aus")

    punkte, wegpunkte = gpx_lesen(args.gpx)
    roh = len(punkte)
    punkte = glaetten(ausduennen_nach_abstand(punkte, MIN_ABSTAND_M), args.glaetten)
    gesamt_km = distanzen_setzen(punkte)
    auf, ab = hoehenmeter(punkte)
    hoehen = [p["ele"] for p in punkte]

    ziel = DATA / "tracks" / f"{args.tag}.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps({"id": args.tag, "punkte": punkte, "wegpunkte": wegpunkte},
                               ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{ziel.relative_to(ROOT)}: {roh} → {len(punkte)} Punkte, {ziel.stat().st_size / 1024:.0f} KB")

    reise_pfad = DATA / "reise.json"
    reise = json.loads(reise_pfad.read_text(encoding="utf-8"))
    etappe = next((x for x in reise["etappen"] if x["id"] == args.tag), None)
    neu = etappe is None
    if neu:
        nummer = int(args.tag.split("-")[1])
        etappe = {
            "id": args.tag, "nr": nummer,
            "von": args.von or "?", "nach": args.nach or "?",
            "datum": args.datum or "1970-01-01",
            "luecke": None, "geplant": [], "paesse": [], "strava": [],
            "uebernachtung": None, "zusammenfassung": [], "fotos": [],
        }
        reise["etappen"].append(etappe)
        reise["etappen"].sort(key=lambda x: x["nr"])
        if not args.datum:
            print("  Achtung: kein --datum angegeben, bitte in data/reise.json nachtragen")

    etappe.update({
        "distanzKm": round(gesamt_km, 1),
        "aufstiegM": round(auf), "abstiegM": round(ab),
        "minHoehe": round(min(hoehen)), "maxHoehe": round(max(hoehen)),
        "profil": profil_stuetzen(punkte, PROFIL_STUETZEN),
        "start": [punkte[0]["lat"], punkte[0]["lon"]],
        "ziel": [punkte[-1]["lat"], punkte[-1]["lon"]],
    })
    reise_pfad.write_text(json.dumps(reise, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  data/reise.json: {round(gesamt_km, 1)} km, +{round(auf)} m, −{round(ab)} m, "
          f"{round(min(hoehen))}–{round(max(hoehen))} m" + (" (Etappe neu angelegt)" if neu else ""))

    # Übersichtskarte aus allen vorhandenen Tracks neu aufbauen.
    uebersicht = []
    for x in reise["etappen"]:
        pfad = DATA / "tracks" / f'{x["id"]}.json'
        if not pfad.exists():
            continue
        track = json.loads(pfad.read_text(encoding="utf-8"))
        uebersicht.append({
            "id": x["id"], "nr": x["nr"],
            "punkte": [[round(p["lat"], 5), round(p["lon"], 5)]
                       for p in gleichmaessig(track["punkte"], MAX_UEBERSICHT_PUNKTE)],
        })
    (DATA / "uebersicht.json").write_text(
        json.dumps(uebersicht, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"  data/uebersicht.json: {len(uebersicht)} Etappen")
    print("\nJetzt noch:  python3 tools/build.py")


if __name__ == "__main__":
    main()
