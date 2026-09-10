#!/usr/bin/env python3
"""Erzeugt alle HTML-Seiten aus templates/ und data/.

    python3 tools/build.py            # Seiten schreiben
    python3 tools/build.py --check    # nur prüfen, ob die Dateien aktuell sind

Geschrieben werden index.html, etappen.html, packliste.html und
tag-01.html … tag-14.html. Inhalte, Zahlen, Pass-Chips, Übernachtung,
Zusammenfassung und Fotoraster stehen danach fest im HTML -- JavaScript
übernimmt nur Karte, Höhenprofil, Lightbox und die Packlisten-Häkchen.

Der Reisestatus (gefahren / heute / geplant) wird beim Bauen gegen das
heutige Datum bestimmt. Also: vor dem Hochladen neu bauen.
"""
import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
DATA = ROOT / "data"

WOCHENTAG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WOCHENTAG_KURZ = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
MONAT = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
         "August", "September", "Oktober", "November", "Dezember"]
MONAT_KURZ = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli",
              "Aug.", "Sep.", "Okt.", "Nov.", "Dez."]

# Farben der Packlisten-Gruppen: von Bleu über neutrale Töne nach Rouge.
GRUPPEN_FARBEN = ["#003d78", "#0055a4", "#3d7dc0", "#7aa6d6", "#a8b6c8",
                  "#c8102e", "#ef4135", "#f2887f", "#5c6a80"]


# --- Formate ---------------------------------------------------------------

def zahl(n):
    return f"{round(n):,}".replace(",", ".")


def km(v):
    ganz, komma = f"{v:.1f}".split(".")
    return f"{int(ganz):,}".replace(",", ".") + "," + komma + " km"


def meter(n, vorzeichen=""):
    z = zahl(abs(n)) + " m"
    return {"+": "+", "-": "−"}.get(vorzeichen, "") + z


def gramm(g):
    if g >= 1000:
        return f"{g / 1000:.2f}".replace(".", ",") + " kg"
    return zahl(g) + " g"


def tag_datum(iso):
    d = date.fromisoformat(iso)
    return d


def datum_kurz(iso):
    d = tag_datum(iso)
    return f"{WOCHENTAG_KURZ[d.weekday()]}, {d.day}. {MONAT_KURZ[d.month - 1]}"


def datum_lang(iso):
    d = tag_datum(iso)
    return f"{WOCHENTAG[d.weekday()]}, {d.day}. {MONAT[d.month - 1]} {d.year}"


def zeitraum(von, bis):
    a, b = tag_datum(von), tag_datum(bis)
    if a.year == b.year:
        if a.month == b.month:
            return f"{a.day}.–{b.day}. {MONAT[b.month - 1]} {b.year}"
        return f"{a.day}. {MONAT[a.month - 1]} – {b.day}. {MONAT[b.month - 1]} {b.year}"
    return f"{a.day}. {MONAT[a.month - 1]} {a.year} – {b.day}. {MONAT[b.month - 1]} {b.year}"


def e(text):
    """HTML-escapen; None wird zu leerem String."""
    return html.escape(str(text), quote=True) if text is not None else ""


# --- Status ----------------------------------------------------------------

STATUS_LABEL = {"gefahren": "gefahren", "heute": "heute", "geplant": "geplant"}


def status_von(iso, heute):
    d = tag_datum(iso)
    if d < heute:
        return "gefahren"
    return "heute" if d == heute else "geplant"


def status_badge(status):
    return f'<span class="status status-{status}">{STATUS_LABEL[status]}</span>'


# --- Bausteine -------------------------------------------------------------

def kennzahl(label, wert, klasse=""):
    k = f' class="{klasse}"' if klasse else ""
    return f"<div><dt>{e(label)}</dt><dd{k}>{wert}</dd></div>"


def pass_chips(paesse):
    if not paesse:
        return ""
    teile = []
    for p in paesse:
        inner = f'<b>{e(p["name"])}</b><span class="hoehe">{zahl(p["hoehe"])} m</span>'
        klassen = "pass-chip" + (" manuell" if p.get("manuell") else "")
        if p.get("url"):
            titel = ' title="Von Hand ergänzt — die Strava-Aufzeichnung war mitten am Berg geteilt."' if p.get("manuell") else ""
            teile.append(f'<a class="{klassen}" href="{e(p["url"])}" target="_blank" rel="noopener"{titel}>{inner}</a>')
        else:
            teile.append(f'<span class="pass-chip ohne-link" title="Noch keine quäldich-Seite verlinkt">{inner}</span>')
    return "".join(teile)


def strava_chips(etappe, status):
    if etappe["strava"]:
        return " ".join(
            f'<a class="strava" href="https://www.strava.com/activities/{e(a["id"])}"'
            f' target="_blank" rel="noopener">{e(a["name"])}</a>'
            for a in etappe["strava"]
        )
    text = "Noch nicht gefahren" if status == "geplant" else "Keine Aufzeichnung"
    return f'<span class="strava stumm">{text}</span>'


def sparkline(profil, breite=260, hoehe=34, rand=3):
    lo, hi = min(profil), max(profil)
    spanne = max(1, hi - lo)
    punkte = []
    for i, wert in enumerate(profil):
        x = rand + (i / (len(profil) - 1)) * (breite - rand * 2)
        y = hoehe - rand - ((wert - lo) / spanne) * (hoehe - rand * 2)
        punkte.append(f"{x:.1f} {y:.1f}")
    linie = "M" + " L".join(punkte)
    flaeche = f"{linie} L{breite - rand:.1f} {hoehe} L{rand:.1f} {hoehe} Z"
    return (f'<svg class="sparkline" viewBox="0 0 {breite} {hoehe}" preserveAspectRatio="none" aria-hidden="true">'
            f'<path class="flaeche" d="{flaeche}"/><path class="linie" d="{linie}"/></svg>')


def etappen_name(etappe):
    return f'{etappe["von"]} → {etappe["nach"]}'


# --- Seitenrahmen ----------------------------------------------------------

def rahmen(reise, inhalt, *, titel, beschreibung, css_extra, skripte, aktiv, og_titel=None):
    kopf = (TEMPLATES / "_kopf.html").read_text(encoding="utf-8")
    fuss = (TEMPLATES / "_fuss.html").read_text(encoding="utf-8")
    nav = {"start": "", "etappen": "", "packliste": ""}
    nav[aktiv] = ' aria-current="page"'
    kopf = fuellen(kopf, {
        "titel": e(titel),
        "beschreibung": e(beschreibung),
        "og_titel": e(og_titel or titel),
        "marke": e(reise["titel"]),
        "css_extra": css_extra,
        "nav_start": nav["start"],
        "nav_etappen": nav["etappen"],
        "nav_packliste": nav["packliste"],
    })
    fuss = fuellen(fuss, {
        "stravaProfil": e(reise["stravaProfil"]),
        "quaeldichProfil": e(reise["quaeldichProfil"]),
        "skripte": skripte,
    })
    return kopf + inhalt + fuss


def fuellen(vorlage, werte):
    for schluessel, wert in werte.items():
        vorlage = vorlage.replace("{{" + schluessel + "}}", wert)
    return vorlage


def pruefen_vollstaendig(name, text):
    if "{{" in text:
        rest = text[text.index("{{"):text.index("{{") + 40]
        sys.exit(f"{name}: unersetzter Platzhalter {rest!r}")


# --- Startseite ------------------------------------------------------------

def seite_start(reise, heute):
    etappen = reise["etappen"]
    gesamt_km = sum(x["distanzKm"] for x in etappen)
    gesamt_hm = sum(x["aufstiegM"] for x in etappen)
    paesse = sum(len(x["paesse"]) for x in etappen)
    gefahren = [x for x in etappen if status_von(x["datum"], heute) != "geplant"]
    gefahren_km = sum(x["distanzKm"] for x in gefahren)
    offen = len(etappen) - len(gefahren)

    kennzahlen = "".join([
        kennzahl("Distanz", km(gesamt_km)),
        kennzahl("Höhenmeter", meter(gesamt_hm, "+"), "wert-auf"),
        kennzahl("Pässe", zahl(paesse) if paesse else "—"),
        kennzahl("Etappen", f"{len(etappen)}"),
    ])

    if reise.get("titelbild"):
        bild = (f'<figure class="hero-bild"><img src="{e(reise["titelbild"]["datei"])}"'
                f' alt="{e(reise["titelbild"].get("titel", ""))}">'
                f'<div class="tricolore" aria-hidden="true"></div></figure>')
    else:
        bild = ('<div class="hero-bild leer">'
                '<p>Hier kommt das Titelbild hin.<br><span class="mono" style="font-size:12px">'
                'data/reise.json → "titelbild"</span></p>'
                '<div class="tricolore" aria-hidden="true"></div></div>')

    # Aufruf zum Weiterklicken: heutige Etappe, sonst letzte gefahrene, sonst erste.
    heutige = next((x for x in etappen if status_von(x["datum"], heute) == "heute"), None)
    ziel_etappe = heutige or (gefahren[-1] if gefahren else etappen[0])
    if heutige:
        cta_text, e3_titel = "Etappe von heute", "Heute"
        e3_text = f'Tag {ziel_etappe["nr"]}: {etappen_name(ziel_etappe)} — {km(ziel_etappe["distanzKm"])}, {meter(ziel_etappe["aufstiegM"], "+")}.'
    elif gefahren:
        cta_text, e3_titel = "Zuletzt gefahren", "Zuletzt gefahren"
        e3_text = f'Tag {ziel_etappe["nr"]}: {etappen_name(ziel_etappe)} — {km(ziel_etappe["distanzKm"])}, {meter(ziel_etappe["aufstiegM"], "+")}.'
    else:
        cta_text, e3_titel = "Erste Etappe", "Der Anfang"
        e3_text = f'Tag 1: {etappen_name(ziel_etappe)} — {km(ziel_etappe["distanzKm"])} den Rhein hinunter.'

    if offen == 0:
        fortschritt_text = f'{reise["ziel"]} erreicht · alle {len(etappen)} Etappen gefahren'
    else:
        fortschritt_text = (f'{len(gefahren)} von {len(etappen)} Etappen gefahren · '
                            f'{km(gefahren_km)} von {km(gesamt_km)} · noch {offen} '
                            f'{"Etappe" if offen == 1 else "Etappen"}')

    zeilen = []
    for x in etappen:
        st = status_von(x["datum"], heute)
        paesse_text = ", ".join(p["name"] for p in x["paesse"]) or \
            (", ".join(x["geplant"]) + " (geplant)" if x["geplant"] else "—")
        zeilen.append(
            f'<tr class="{"ist-heute" if st == "heute" else ""}">'
            f'<td class="nr">{x["nr"]}</td>'
            f'<td class="mono" style="white-space:nowrap">{e(datum_kurz(x["datum"]))}</td>'
            f'<td><a href="{x["id"]}.html">{e(etappen_name(x))}</a> {status_badge(st) if st != "gefahren" else ""}</td>'
            f'<td class="zahl">{km(x["distanzKm"])}</td>'
            f'<td class="zahl wert-auf">{meter(x["aufstiegM"], "+")}</td>'
            f'<td class="paesse-zelle">{e(paesse_text)}</td></tr>')

    summe = (f'<tr><td></td><td></td><td>Gesamt</td>'
             f'<td class="zahl">{km(gesamt_km)}</td>'
             f'<td class="zahl wert-auf">{meter(gesamt_hm, "+")}</td><td></td></tr>')

    inhalt = fuellen((TEMPLATES / "index.html").read_text(encoding="utf-8"), {
        "eyebrow": f'Bikepacking · {len(etappen)} Etappen',
        "titel": e(reise["titel"]),
        "route": f'{e(reise["start"])} → {e(reise["ziel"])}',
        "zeitraum": e(zeitraum(reise["von"], reise["bis"])),
        "kennzahlen": kennzahlen,
        "fortschritt": f'{gefahren_km / gesamt_km * 100:.1f}',
        "fortschritt_text": e(fortschritt_text),
        "cta_ziel": f'{ziel_etappe["id"]}.html',
        "cta_text": e(cta_text),
        "titelbild": bild,
        "anzahl_etappen": str(len(etappen)),
        "start_ort": e(reise["start"]),
        "ziel_ort": e(reise["ziel"]),
        "einstieg3_titel": e(e3_titel),
        "einstieg3_text": e(e3_text),
        "tabelle": "".join(zeilen),
        "tabelle_summe": summe,
        "tabelle_note": "Distanzen und Höhenmeter aus den aufgezeichneten bzw. geplanten Tracks.",
    })
    pruefen_vollstaendig("index.html", inhalt)

    status_map = {x["id"]: status_von(x["datum"], heute) for x in etappen}
    namen_map = {x["id"]: etappen_name(x) for x in etappen}
    skripte = (
        '<script src="assets/vendor/leaflet/leaflet.js"></script>\n'
        '<script src="assets/js/format.js"></script>\n'
        '<script src="assets/js/karte.js"></script>\n'
        f'<script>window.RGA_STATUS={json.dumps(status_map, ensure_ascii=False)};'
        f'window.RGA_NAMEN={json.dumps(namen_map, ensure_ascii=False)};</script>\n'
        '<script src="assets/js/start.js"></script>'
    )
    return rahmen(
        reise, inhalt,
        titel=f'{reise["titel"]} — Bikepacking auf der Route des Grandes Alpes',
        beschreibung=(f'{km(gesamt_km)} und {meter(gesamt_hm, "+")} von {reise["start"]} nach '
                      f'{reise["ziel"]}: {len(etappen)} Etappen mit Karten, Höhenprofilen, '
                      f'Übernachtungen, Fotos und Packliste.'),
        css_extra='<link rel="stylesheet" href="assets/css/site.css">\n'
                  '<link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css">',
        skripte=skripte, aktiv="start",
    )


# --- Etappenübersicht ------------------------------------------------------

def seite_etappen(reise, heute):
    etappen = reise["etappen"]
    gesamt_km = sum(x["distanzKm"] for x in etappen)
    gesamt_hm = sum(x["aufstiegM"] for x in etappen)
    gesamt_ab = sum(x["abstiegM"] for x in etappen)
    hoechster = max(etappen, key=lambda x: x["maxHoehe"])

    karten = []
    for x in etappen:
        st = status_von(x["datum"], heute)
        paesse = " · ".join(p["name"] for p in x["paesse"]) or " · ".join(x["geplant"])
        karten.append(
            f'<a class="etappe-karte ist-{st}" href="{x["id"]}.html">'
            f'<span class="etappe-kopf"><span class="etappe-nr">Tag {x["nr"]}</span>'
            f'<span class="etappe-datum">{e(datum_kurz(x["datum"]))}</span></span>'
            + f'<span class="etappe-name">{e(etappen_name(x))}</span>'
            + (f'<span class="etappe-paesse">{e(paesse)}</span>' if paesse else "")
            + (f'<span class="etappe-luecke">{e(x["luecke"])}</span>' if x["luecke"] else "")
            + sparkline(x["profil"])
            + f'<span class="etappe-zahlen"><span><b>{km(x["distanzKm"])}</b></span>'
              f'<span><b>{meter(x["aufstiegM"], "+")}</b></span>'
              f'<span><b>{meter(x["abstiegM"], "-")}</b></span></span>'
            + (f'<span>{status_badge(st)}</span>' if st != "gefahren" else "")
            + '</a>')

    mit_paessen = [x for x in etappen if x["paesse"]]
    anzahl_paesse = sum(len(x["paesse"]) for x in mit_paessen)
    if anzahl_paesse:
        manuell = any(p.get("manuell") for x in mit_paessen for p in x["paesse"])
        tage = "".join(
            f'<div class="pass-tag"><span class="pass-tag-label">'
            f'<a href="{x["id"]}.html">Tag {x["nr"]} · {e(datum_kurz(x["datum"]))}</a></span>'
            f'<div class="chips">{pass_chips(x["paesse"])}</div></div>'
            for x in mit_paessen)
        panel = (f'<div class="pass-panel"><h3>Gefahrene Pässe · {anzahl_paesse}</h3>'
                 f'<p>Aus den Strava-Notizen, verlinkt auf '
                 f'<a href="{e(reise["quaeldichProfil"])}" target="_blank" rel="noopener">quäldich.de</a>.'
                 + (" Gestrichelt umrandet = von Hand ergänzt." if manuell else "")
                 + f'</p>{tage}</div>')
    else:
        panel = ""

    kennzahlen = "".join([
        kennzahl("Distanz", km(gesamt_km)),
        kennzahl("Aufstieg", meter(gesamt_hm, "+"), "wert-auf"),
        kennzahl("Abstieg", meter(gesamt_ab, "-"), "wert-ab"),
        kennzahl("Höchster Punkt", f'{meter(hoechster["maxHoehe"])}'),
    ])

    inhalt = fuellen((TEMPLATES / "etappen.html").read_text(encoding="utf-8"), {
        "eyebrow": f'{e(reise["start"])} → {e(reise["ziel"])} · {e(zeitraum(reise["von"], reise["bis"]))}',
        "einleitung": (f'{len(etappen)} Tage vom Rhein an die Riviera. Jede Etappe hat ihre eigene Seite '
                       f'mit Karte, Höhenprofil, Übernachtung, Zusammenfassung und Fotos. '
                       f'Der höchste Punkt liegt auf Tag {hoechster["nr"]} bei {meter(hoechster["maxHoehe"])}.'),
        "kennzahlen": kennzahlen,
        "karten": "".join(karten),
        "pass_panel": panel,
    })
    pruefen_vollstaendig("etappen.html", inhalt)
    return rahmen(
        reise, inhalt,
        titel=f'Etappen — {reise["titel"]}',
        beschreibung=(f'Alle {len(etappen)} Etappen von {reise["start"]} nach {reise["ziel"]}: '
                      f'{km(gesamt_km)}, {meter(gesamt_hm, "+")}, {anzahl_paesse} Pässe.'),
        css_extra='<link rel="stylesheet" href="assets/css/site.css">',
        skripte="", aktiv="etappen",
    )


# --- Eine Etappe -----------------------------------------------------------

def sterne(n):
    voll = "★" * int(n)
    leer = "☆" * (5 - int(n))
    return (f'<span class="sterne" title="{n} von 5">{voll}'
            f'<span class="aus">{leer}</span></span>')


def block_uebernachtung(etappe):
    u = etappe.get("uebernachtung")
    if not u:
        return ('<!-- Eintragen in data/reise.json: "uebernachtung": {"name":…, "art":…, "ort":…,'
                ' "url":…, "lat":…, "lon":…, "preisEur":…, "bewertung":…, "notiz":…} -->\n'
                '<p class="leer-hinweis">Für diesen Tag ist noch keine Übernachtung eingetragen.</p>')

    name = e(u["name"])
    if u.get("url"):
        name = f'<a href="{e(u["url"])}" target="_blank" rel="noopener">{name}</a>'

    zahlen = []
    if u.get("preisEur") is not None:
        zahlen.append(kennzahl("Preis", f'{zahl(u["preisEur"])} €'))
    if u.get("bewertung"):
        zahlen.append(f'<div><dt>Bewertung</dt><dd>{sterne(u["bewertung"])}</dd></div>')
    if u.get("hoehe"):
        zahlen.append(kennzahl("Höhe", meter(u["hoehe"])))

    teile = ['<div class="uebernachtung-karte">', '<div class="uebernachtung-kopf">', f'<h3>{name}</h3>']
    if u.get("art"):
        teile.append(f'<span class="art-badge">{e(u["art"])}</span>')
    teile.append('</div>')
    if u.get("ort"):
        teile.append(f'<p class="uebernachtung-ort">{e(u["ort"])}</p>')
    if u.get("notiz"):
        teile.append(f'<p class="uebernachtung-notiz">{e(u["notiz"])}</p>')
    if zahlen:
        teile.append(f'<dl class="kennzahlen uebernachtung-zahlen">{"".join(zahlen)}</dl>')
    teile.append('</div>')

    if u.get("lat") and u.get("lon"):
        teile.append('<p class="uebernachtung-hinweis">'
                     'Auf der Karte oben ist die Übernachtung mit einer Fahne markiert.</p>')
    return f'<div class="uebernachtung">{"".join(teile)}</div>'


def block_zusammenfassung(etappe):
    absaetze = etappe.get("zusammenfassung") or []
    if not absaetze:
        return ('<!-- Eintragen in data/reise.json: "zusammenfassung": ["Erster Absatz", "Zweiter Absatz"] -->\n'
                '<p class="leer-hinweis">Die Zusammenfassung zu diesem Tag fehlt noch.</p>')
    return ('<div class="zusammenfassung">'
            + "".join(f"<p>{e(a)}</p>" for a in absaetze) + "</div>")


def block_fotos(etappe):
    fotos = etappe.get("fotos") or []
    if not fotos:
        return ('<!-- Bilder nach fotos/{id}/ legen, Thumbs mit tools/fotos_vorbereiten.py erzeugen,\n'
                '     dann in data/reise.json: "fotos": [{"datei": "img_1234.jpg", "titel": "…"}] -->\n'
                '<p class="leer-hinweis">Für diesen Tag sind noch keine Fotos eingepflegt.</p>').replace(
                    "{id}", etappe["id"])
    ordner = f'fotos/{etappe["id"]}'
    knoepfe = []
    for f in fotos:
        titel = e(f.get("titel", ""))
        knoepfe.append(
            f'<li><button type="button" data-gross="{ordner}/{e(f["datei"])}" data-titel="{titel}">'
            f'<img src="{ordner}/thumbs/{e(f["datei"])}" alt="{titel}" loading="lazy" decoding="async">'
            f'</button></li>')
    return f'<ul class="foto-raster" id="fotoRaster">{"".join(knoepfe)}</ul>'


def seite_tag(reise, etappe, heute):
    etappen = reise["etappen"]
    st = status_von(etappe["datum"], heute)
    nr = etappe["nr"]
    kennzahlen = "".join([
        kennzahl("Distanz", km(etappe["distanzKm"])),
        kennzahl("Aufstieg", meter(etappe["aufstiegM"], "+"), "wert-auf"),
        kennzahl("Abstieg", meter(etappe["abstiegM"], "-"), "wert-ab"),
        kennzahl("Höhe", f'{zahl(etappe["minHoehe"])}–{zahl(etappe["maxHoehe"])} m'),
        kennzahl("Pässe", str(len(etappe["paesse"])) if etappe["paesse"] else "—"),
    ])
    luecke = (f'<p class="tag-luecke"><b>Lücke im Track:</b> {e(etappe["luecke"])}</p>'
              if etappe["luecke"] else "")
    paesse = pass_chips(etappe["paesse"]) or (
        f'<span class="chip-leer">Geplant: {e(", ".join(etappe["geplant"]))}</span>'
        if etappe["geplant"] else '<span class="chip-leer">keine</span>')

    nachbarn = []
    if nr > 1:
        v = etappen[nr - 2]
        nachbarn.append(f'<a class="zurueck" href="{v["id"]}.html"><span class="richtung">← Tag {v["nr"]}</span>'
                        f'<span class="ziel-name">{e(etappen_name(v))}</span></a>')
    if nr < len(etappen):
        n = etappen[nr]
        nachbarn.append(f'<a class="weiter" href="{n["id"]}.html"><span class="richtung">Tag {n["nr"]} →</span>'
                        f'<span class="ziel-name">{e(etappen_name(n))}</span></a>')

    streifen = "".join(
        f'<a class="ist-{status_von(x["datum"], heute)}" href="{x["id"]}.html"'
        + (' aria-current="page"' if x["id"] == etappe["id"] else "")
        + f'><span class="nr">Tag {x["nr"]}</span>'
          f'<span class="ort">{e(x["nach"])}</span>'
          f'<span class="km">{km(x["distanzKm"])}</span></a>'
        for x in etappen)

    fotos = etappe.get("fotos") or []
    inhalt = fuellen((TEMPLATES / "tag.html").read_text(encoding="utf-8"), {
        "nr": str(nr),
        "anzahl": str(len(etappen)),
        "datum": e(datum_lang(etappe["datum"])),
        "status_badge": status_badge(st),
        "von": e(etappe["von"]),
        "nach": e(etappe["nach"]),
        "luecke": luecke,
        "kennzahlen": kennzahlen,
        "pass_label": "Pass" if len(etappe["paesse"]) == 1 else "Pässe",
        "paesse": paesse,
        "strava": strava_chips(etappe, st),
        "profil_beschreibung": e(f'{zahl(etappe["minHoehe"])} bis {zahl(etappe["maxHoehe"])} Meter, '
                                 f'insgesamt {meter(etappe["aufstiegM"], "+")} auf {km(etappe["distanzKm"])}'),
        "uebernachtung": block_uebernachtung(etappe),
        "zusammenfassung": block_zusammenfassung(etappe),
        "foto_anzahl": f'<span class="foto-anzahl">{len(fotos)}</span>' if fotos else "",
        "fotos": block_fotos(etappe),
        "nachbarn": "".join(nachbarn),
        "streifen": streifen,
    })
    pruefen_vollstaendig(f'{etappe["id"]}.html', inhalt)

    u = etappe.get("uebernachtung") or {}
    bett = None
    if u.get("lat") and u.get("lon"):
        bett = {"pos": [u["lat"], u["lon"]],
                "html": f'<b>{u["name"]}</b>' + (f'{u.get("art", "")} · Übernachtung Tag {nr}')}
    meta = {"id": etappe["id"], "status": st, "von": etappe["von"], "nach": etappe["nach"], "bett": bett}
    skripte = (
        '<script src="assets/vendor/leaflet/leaflet.js"></script>\n'
        '<script src="assets/js/format.js"></script>\n'
        '<script src="assets/js/karte.js"></script>\n'
        '<script src="assets/js/profil.js"></script>\n'
        '<script src="assets/js/lightbox.js"></script>\n'
        f'<script>window.RGA_TAG={json.dumps(meta, ensure_ascii=False)};</script>\n'
        '<script src="assets/js/tag.js"></script>'
    )
    beschreibung = (f'Tag {nr} von {len(etappen)} auf der Route des Grandes Alpes: '
                    f'{etappen_name(etappe)}, {km(etappe["distanzKm"])} und {meter(etappe["aufstiegM"], "+")}'
                    + (f' über {", ".join(p["name"] for p in etappe["paesse"])}.' if etappe["paesse"] else "."))
    return rahmen(
        reise, inhalt,
        titel=f'Tag {nr}: {etappen_name(etappe)} — {reise["titel"]}',
        og_titel=f'Tag {nr}: {etappen_name(etappe)}',
        beschreibung=beschreibung,
        css_extra='<link rel="stylesheet" href="assets/css/site.css">\n'
                  '<link rel="stylesheet" href="assets/css/tag.css">\n'
                  '<link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css">',
        skripte=skripte, aktiv="etappen",
    )


# --- Packliste -------------------------------------------------------------

def gruppen_anker(name):
    tabelle = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", " ": "-", "&": "und"})
    return "gruppe-" + "".join(
        c for c in name.lower().translate(tabelle) if c.isalnum() or c == "-").strip("-")


def seite_packliste(reise, pack):
    gruppen_html, legende, verteilung = [], [], []
    gepaeck = 0
    summen = []
    for i, g in enumerate(pack["gruppen"]):
        farbe = GRUPPEN_FARBEN[i % len(GRUPPEN_FARBEN)]
        summe = sum(p["anzahl"] * p["gramm"] for p in g["posten"])
        summen.append((g, farbe, summe))
        if not g.get("amKoerper"):
            gepaeck += summe

    for g, farbe, summe in summen:
        posten = []
        for p in g["posten"]:
            pid = f'{g["name"]}|{p["name"]}'
            gesamt = p["anzahl"] * p["gramm"]
            urteil = ""
            if p.get("wiederMitnehmen") is True:
                urteil = '<span class="pack-urteil ja">wieder dabei</span>'
            elif p.get("wiederMitnehmen") is False:
                urteil = '<span class="pack-urteil nein">bleibt daheim</span>'
            anzahl = f'<span class="pack-anzahl">×{p["anzahl"]}</span>' if p["anzahl"] > 1 else ""
            posten.append(
                f'<li class="pack-zeile">'
                f'<input type="checkbox" id="{e(pid)}" data-id="{e(pid)}" data-gramm="{gesamt}">'
                f'<label for="{e(pid)}"><span class="pack-name">{e(p["name"])}</span>{anzahl}{urteil}</label>'
                f'<span class="pack-gewicht">{gramm(gesamt)}</span>'
                + (f'<p class="pack-notiz">{e(p["notiz"])}</p>' if p.get("notiz") else "")
                + '</li>')
        gruppen_html.append(
            f'<section class="pack-gruppe"><div class="pack-gruppe-kopf">'
            f'<h3><i style="background:{farbe}"></i>{e(g["name"])}</h3>'
            f'<span class="pack-gruppe-gewicht">{gramm(summe)} · {len(g["posten"])} Posten</span>'
            + (f'<p class="pack-gruppe-note">{e(g["notiz"])}</p>' if g.get("notiz") else "")
            + f'</div><ul class="pack-liste">{"".join(posten)}</ul></section>')
        if not g.get("amKoerper"):
            verteilung.append(f'<i style="background:{farbe}; width:{summe / gepaeck * 100:.2f}%" '
                              f'title="{e(g["name"])}: {gramm(summe)}"></i>')
            legende.append(f'<div><i style="background:{farbe}"></i>{e(g["name"])}<b>{gramm(summe)}</b></div>')

    am_koerper = sum(s for g, _, s in summen if g.get("amKoerper"))
    leer = pack.get("leergewichte") or []
    note_teile = [f'in {len([g for g, _, _ in summen if not g.get("amKoerper")])} Gruppen, ohne Rad']
    if am_koerper:
        note_teile.append(f'am Körper zusätzlich {gramm(am_koerper)}')
    for l in leer:
        note_teile.append(f'{l["name"]}: {gramm(l["gramm"])}')

    sprung = "".join(
        f'<a class="pack-sprung" href="#{gruppen_anker(g["name"])}">{e(g["name"])}'
        f'<b>{gramm(summe)}</b></a>'
        for g, _, summe in summen)

    wert = gramm(gepaeck).split(" ")
    inhalt = fuellen((TEMPLATES / "packliste.html").read_text(encoding="utf-8"), {
        "eyebrow": f'{e(reise["start"])} → {e(reise["ziel"])} · {e(zeitraum(reise["von"], reise["bis"]))}',
        "einleitung": e(pack.get("einleitung", "")),
        "gesamt": wert[0],
        "gesamt_einheit": wert[1],
        "gesamt_note": e(" · ".join(note_teile)),
        "verteilung": "".join(verteilung),
        "verteilung_legende": "".join(legende),
        "sprungliste": sprung,
        "gruppen": "".join(gruppen_html),
    })
    pruefen_vollstaendig("packliste.html", inhalt)
    return rahmen(
        reise, inhalt,
        titel=f'Packliste — {reise["titel"]}',
        beschreibung=(f'Was auf {km(sum(x["distanzKm"] for x in reise["etappen"]))} von '
                      f'{reise["start"]} nach {reise["ziel"]} mitfuhr: {gramm(gepaeck)} Gepäck '
                      f'in {len(pack["gruppen"])} Gruppen, mit Gewichten und Fazit.'),
        css_extra='<link rel="stylesheet" href="assets/css/site.css">',
        skripte='<script src="assets/js/format.js"></script>\n'
                '<script src="assets/js/packliste.js"></script>',
        aktiv="packliste",
    )


# --- Hauptlauf -------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Erzeugt die HTML-Seiten aus templates/ und data/.")
    ap.add_argument("--check", action="store_true",
                    help="nichts schreiben, nur melden, welche Seiten veraltet sind")
    ap.add_argument("--heute", metavar="JJJJ-MM-TT",
                    help="Stichtag für gefahren/heute/geplant (Vorgabe: heute)")
    args = ap.parse_args()
    heute = date.fromisoformat(args.heute) if args.heute else date.today()

    reise = json.loads((DATA / "reise.json").read_text(encoding="utf-8"))
    pack = json.loads((DATA / "packliste.json").read_text(encoding="utf-8"))
    etappen = reise["etappen"]
    if [x["nr"] for x in etappen] != list(range(1, len(etappen) + 1)):
        sys.exit("reise.json: 'nr' muss von 1 an lückenlos aufsteigen")

    seiten = {
        "index.html": seite_start(reise, heute),
        "etappen.html": seite_etappen(reise, heute),
        "packliste.html": seite_packliste(reise, pack),
    }
    for etappe in etappen:
        seiten[f'{etappe["id"]}.html'] = seite_tag(reise, etappe, heute)

    veraltet = []
    for name, text in sorted(seiten.items()):
        ziel = ROOT / name
        alt = ziel.read_text(encoding="utf-8") if ziel.exists() else None
        if alt == text:
            continue
        veraltet.append(name)
        if not args.check:
            ziel.write_text(text, encoding="utf-8")

    if args.check:
        if veraltet:
            print("Nicht aktuell: " + ", ".join(veraltet))
            sys.exit(1)
        print(f"Alle {len(seiten)} Seiten sind aktuell (Stichtag {heute.isoformat()}).")
        return

    print(f"{len(seiten)} Seiten geprüft, {len(veraltet)} geschrieben (Stichtag {heute.isoformat()}):")
    for name in veraltet:
        print(f'  {name}  {(ROOT / name).stat().st_size / 1024:.0f} KB')


if __name__ == "__main__":
    main()
