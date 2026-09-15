#!/usr/bin/env python3
"""Builds the whole site from gpx/ and data/.

    python3 tools/build.py                    write everything
    python3 tools/build.py --check            only report what is out of date
    python3 tools/build.py --smoothing 0      no elevation smoothing

Inputs
    gpx/day-NN.gpx           one track per stage, the source for every number
    data/trip.json           hand-written stage content
    data/packing-list.json   the packing list

Outputs
    index.html, stages.html, packing-list.html, day-NN.html
    data/tracks/day-NN.json  thinned geometry, fetched when a stage opens
    data/overview.json       all stages, thinned further, for the landing map

Text, figures, pass chips, lodging, summaries and photo grids end up in the
HTML, so JavaScript only drives the map, the profile, the lightbox and the
packing-list checkboxes.

The trip is finished and its dates are fixed, so there is no ridden/planned
distinction to work out -- every stage is simply done.
"""
import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

import gpx

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
DATA = ROOT / "data"
GPX_DIR = ROOT / "gpx"

WEEKDAY = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WEEKDAY_SHORT = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
MONTH = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
         "August", "September", "Oktober", "November", "Dezember"]
MONTH_SHORT = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli",
               "Aug.", "Sep.", "Okt.", "Nov.", "Dez."]

# Packing-list group colours: from blue through neutral tones to red.
GROUP_COLOURS = ["#003d78", "#0055a4", "#3d7dc0", "#7aa6d6", "#a8b6c8",
                 "#c8102e", "#ef4135", "#f2887f", "#5c6a80"]

# --- German formats --------------------------------------------------------

def number(n):
    return f"{round(n):,}".replace(",", ".")


def km(value):
    whole, fraction = f"{value:.1f}".split(".")
    return f"{int(whole):,}".replace(",", ".") + "," + fraction + " km"


def metres(n, sign=""):
    text = number(abs(n)) + " m"
    return {"+": "+", "-": "−"}.get(sign, "") + text


def grams(g):
    if g >= 1000:
        return f"{g / 1000:.2f}".replace(".", ",") + " kg"
    return number(g) + " g"


def short_date(iso):
    d = date.fromisoformat(iso)
    return f"{WEEKDAY_SHORT[d.weekday()]}, {d.day}. {MONTH_SHORT[d.month - 1]}"


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{WEEKDAY[d.weekday()]}, {d.day}. {MONTH[d.month - 1]} {d.year}"


def date_range(first, last):
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    if a.year == b.year:
        if a.month == b.month:
            return f"{a.day}.–{b.day}. {MONTH[b.month - 1]} {b.year}"
        return f"{a.day}. {MONTH[a.month - 1]} – {b.day}. {MONTH[b.month - 1]} {b.year}"
    return f"{a.day}. {MONTH[a.month - 1]} {a.year} – {b.day}. {MONTH[b.month - 1]} {b.year}"


def e(text):
    """Escape for HTML; None becomes an empty string."""
    return html.escape(str(text), quote=True) if text is not None else ""


# --- small HTML pieces -----------------------------------------------------

def stat(label, value, css_class=""):
    attr = f' class="{css_class}"' if css_class else ""
    return f"<div><dt>{e(label)}</dt><dd{attr}>{value}</dd></div>"


def pass_chips(passes):
    chips = []
    for p in passes:
        inner = f'<b>{e(p["name"])}</b><span class="ele">{number(p["eleM"])} m</span>'
        classes = "pass-chip" + (" manual" if p.get("manual") else "")
        if p.get("url"):
            title = (' title="Von Hand ergänzt — die Strava-Aufzeichnung war mitten am Berg geteilt."'
                     if p.get("manual") else "")
            chips.append(f'<a class="{classes}" href="{e(p["url"])}" target="_blank"'
                         f' rel="noopener"{title}>{inner}</a>')
        else:
            chips.append(f'<span class="pass-chip nolink"'
                         f' title="Noch keine quäldich-Seite verlinkt">{inner}</span>')
    return "".join(chips)


def strava_chips(stage):
    if stage["strava"]:
        return " ".join(
            f'<a class="strava" href="https://www.strava.com/activities/{e(a["id"])}"'
            f' target="_blank" rel="noopener">{e(a["name"])}</a>'
            for a in stage["strava"]
        )
    return '<span class="strava muted">Keine Aufzeichnung</span>'


def sparkline(profile, width=260, height=34, pad=3):
    low, high = min(profile), max(profile)
    span = max(1, high - low)
    points = []
    for i, value in enumerate(profile):
        x = pad + (i / (len(profile) - 1)) * (width - pad * 2)
        y = height - pad - ((value - low) / span) * (height - pad * 2)
        points.append(f"{x:.1f} {y:.1f}")
    line = "M" + " L".join(points)
    area = f"{line} L{width - pad:.1f} {height} L{pad:.1f} {height} Z"
    return (f'<svg class="sparkline" viewBox="0 0 {width} {height}" preserveAspectRatio="none"'
            f' aria-hidden="true"><path class="area" d="{area}"/>'
            f'<path class="line" d="{line}"/></svg>')


def stage_name(stage):
    return f'{stage["from"]} → {stage["to"]}'


def fill(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def assert_filled(name, text):
    if "{{" in text:
        snippet = text[text.index("{{"):text.index("{{") + 40]
        sys.exit(f"{name}: placeholder left unfilled: {snippet!r}")


def page(trip, body, *, title, description, extra_css, scripts, active, og_title=None):
    header = (TEMPLATES / "_header.html").read_text(encoding="utf-8")
    footer = (TEMPLATES / "_footer.html").read_text(encoding="utf-8")
    nav = {"home": "", "stages": "", "packing": ""}
    nav[active] = ' aria-current="page"'
    header = fill(header, {
        "title": e(title),
        "description": e(description),
        "og_title": e(og_title or title),
        "brand": e(trip["title"]),
        "extra_css": extra_css,
        "nav_home": nav["home"],
        "nav_stages": nav["stages"],
        "nav_packing": nav["packing"],
    })
    footer = fill(footer, {
        "strava_profile": e(trip["stravaProfile"]),
        "quaeldich_profile": e(trip["quaeldichProfile"]),
        "scripts": scripts,
    })
    return header + body + footer


# --- loading ---------------------------------------------------------------

def load_stages(smoothing):
    """Merge every gpx/*.gpx with its entry in data/trip.json."""
    trip = json.loads((DATA / "trip.json").read_text(encoding="utf-8"))
    content = {s["id"]: s for s in trip["stages"]}
    files = sorted(GPX_DIR.glob("*.gpx"))
    if not files:
        sys.exit(f"no GPX files in {GPX_DIR.relative_to(ROOT)}/ -- nothing to build")

    stages, tracks = [], {}
    for path in files:
        sid = path.stem
        if sid not in content:
            sys.exit(f"{path.name}: no entry with \"id\": \"{sid}\" in data/trip.json.\n"
                     f"  Add at least: {{\"id\": \"{sid}\", \"no\": N, \"from\": \"…\", "
                     f"\"to\": \"…\", \"date\": \"YYYY-MM-DD\"}}")
        try:
            measured = gpx.parse(path, smoothing=smoothing)
        except gpx.GpxError as error:
            sys.exit(str(error))

        stage = dict(content[sid])
        for field in ("no", "from", "to", "date"):
            if not stage.get(field):
                sys.exit(f'data/trip.json, {sid}: "{field}" is missing')
        stage.update(measured)
        stage.setdefault("passes", [])
        stage.setdefault("plannedPasses", [])
        stage.setdefault("strava", [])
        stage.setdefault("summary", [])
        stage.setdefault("photos", [])
        stages.append(stage)
        tracks[sid] = {
            "id": sid,
            "points": measured["points"],
            "waypoints": measured["waypoints"],
        }

    missing_gpx = [sid for sid in content if sid not in tracks]
    if missing_gpx:
        sys.exit("data/trip.json lists stages without a GPX file: "
                 + ", ".join(f"{sid} (expected gpx/{sid}.gpx)" for sid in sorted(missing_gpx)))

    stages.sort(key=lambda s: s["no"])
    if [s["no"] for s in stages] != list(range(1, len(stages) + 1)):
        sys.exit('data/trip.json: "no" must run 1..N without gaps or duplicates')
    return trip, stages, tracks


# --- landing page ----------------------------------------------------------

def render_home(trip, stages):
    total_km = sum(s["distanceKm"] for s in stages)
    total_up = sum(s["ascentM"] for s in stages)
    pass_count = sum(len(s["passes"]) for s in stages)
    start_place, end_place = stages[0]["from"], stages[-1]["to"]

    if trip.get("coverPhoto"):
        cover = (f'<figure class="hero-image"><img src="{e(trip["coverPhoto"]["file"])}"'
                 f' alt="{e(trip["coverPhoto"].get("caption", ""))}">'
                 f'<div class="tricolore" aria-hidden="true"></div></figure>')
    else:
        cover = ('<div class="hero-image empty">'
                 '<p>Hier kommt das Titelbild hin.<br><span class="mono" style="font-size:12px">'
                 'data/trip.json → "coverPhoto"</span></p>'
                 '<div class="tricolore" aria-hidden="true"></div></div>')

    target = stages[-1]
    cta_text = card_title = "Ankunft"
    card_text = (f'Tag {target["no"]}: {stage_name(target)} — {km(target["distanceKm"])}, '
                 f'{metres(target["ascentM"], "+")}.')

    rows = []
    for s in stages:
        passes = ", ".join(p["name"] for p in s["passes"]) or (
            ", ".join(s["plannedPasses"]) + " (geplant)" if s["plannedPasses"] else "—")
        rows.append(
            '<tr>'
            f'<td class="index">{s["no"]}</td>'
            f'<td class="mono" style="white-space:nowrap">{e(short_date(s["date"]))}</td>'
            f'<td><a href="{s["id"]}.html">{e(stage_name(s))}</a></td>'
            f'<td class="num">{km(s["distanceKm"])}</td>'
            f'<td class="num value-up">{metres(s["ascentM"], "+")}</td>'
            f'<td class="passes-cell">{e(passes)}</td></tr>')

    body = fill((TEMPLATES / "index.html").read_text(encoding="utf-8"), {
        "eyebrow": f"Bikepacking · {len(stages)} Etappen",
        "title": e(trip["title"]),
        "route": f"{e(start_place)} → {e(end_place)}",
        "dates": e(date_range(stages[0]["date"], stages[-1]["date"])),
        "stats": "".join([
            stat("Distanz", km(total_km)),
            stat("Höhenmeter", metres(total_up, "+"), "value-up"),
            stat("Pässe", number(pass_count) if pass_count else "—"),
            stat("Etappen", str(len(stages))),
        ]),
        "cta_href": f'{target["id"]}.html',
        "cta_text": e(cta_text),
        "cover": cover,
        "stage_count": str(len(stages)),
        "start_place": e(start_place),
        "end_place": e(end_place),
        "third_card_title": e(card_title),
        "third_card_text": e(card_text),
        "rows": "".join(rows),
        "total_row": (f'<tr><td></td><td></td><td>Gesamt</td>'
                      f'<td class="num">{km(total_km)}</td>'
                      f'<td class="num value-up">{metres(total_up, "+")}</td><td></td></tr>'),
        "table_note": "Distanzen und Höhenmeter sind aus den GPX-Dateien der Etappen berechnet.",
    })
    assert_filled("index.html", body)

    scripts = (
        '<script src="assets/vendor/leaflet/leaflet.js"></script>\n'
        '<script src="assets/js/format.js"></script>\n'
        '<script src="assets/js/map.js"></script>\n'
        f'<script>window.RGA_NAMES={json.dumps({s["id"]: stage_name(s) for s in stages}, ensure_ascii=False)};</script>\n'
        '<script src="assets/js/home.js"></script>'
    )
    return page(
        trip, body,
        title=f'{trip["title"]} — Bikepacking auf der Route des Grandes Alpes',
        description=(f'{km(total_km)} und {metres(total_up, "+")} von {start_place} nach '
                     f'{end_place}: {len(stages)} Etappen mit Karten, Höhenprofilen, '
                     f'Übernachtungen, Fotos und Packliste.'),
        extra_css=('<link rel="stylesheet" href="assets/css/site.css">\n'
                   '<link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css">'),
        scripts=scripts, active="home",
    )


# --- stage overview --------------------------------------------------------

def render_stages(trip, stages):
    total_km = sum(s["distanceKm"] for s in stages)
    total_up = sum(s["ascentM"] for s in stages)
    total_down = sum(s["descentM"] for s in stages)
    highest = max(stages, key=lambda s: s["maxEleM"])

    cards = []
    for s in stages:
        passes = " · ".join(p["name"] for p in s["passes"]) or " · ".join(s["plannedPasses"])
        cards.append(
            f'<a class="stage-card" href="{s["id"]}.html">'
            f'<span class="stage-card-head"><span class="stage-index">Tag {s["no"]}</span>'
            f'<span class="stage-date">{e(short_date(s["date"]))}</span></span>'
            f'<span class="stage-name">{e(stage_name(s))}</span>'
            + (f'<span class="stage-passes">{e(passes)}</span>' if passes else "")
            + (f'<span class="stage-gap">{e(s["gap"])}</span>' if s.get("gap") else "")
            + sparkline(s["profile"])
            + f'<span class="stage-figures"><span><b>{km(s["distanceKm"])}</b></span>'
              f'<span><b>{metres(s["ascentM"], "+")}</b></span>'
              f'<span><b>{metres(s["descentM"], "-")}</b></span></span>'
            + '</a>')

    with_passes = [s for s in stages if s["passes"]]
    pass_count = sum(len(s["passes"]) for s in with_passes)
    if pass_count:
        manual = any(p.get("manual") for s in with_passes for p in s["passes"])
        days = "".join(
            f'<div class="pass-day"><span class="pass-day-label">'
            f'<a href="{s["id"]}.html">Tag {s["no"]} · {e(short_date(s["date"]))}</a></span>'
            f'<div class="chips">{pass_chips(s["passes"])}</div></div>'
            for s in with_passes)
        panel = (f'<div class="pass-panel"><h3>Gefahrene Pässe · {pass_count}</h3>'
                 f'<p>Aus den Strava-Notizen, verlinkt auf '
                 f'<a href="{e(trip["quaeldichProfile"])}" target="_blank" rel="noopener">quäldich.de</a>.'
                 + (" Gestrichelt umrandet = von Hand ergänzt." if manual else "")
                 + f'</p>{days}</div>')
    else:
        panel = ""

    body = fill((TEMPLATES / "stages.html").read_text(encoding="utf-8"), {
        "eyebrow": (f'{e(stages[0]["from"])} → {e(stages[-1]["to"])} · '
                    f'{e(date_range(stages[0]["date"], stages[-1]["date"]))}'),
        "intro": (f'{len(stages)} Tage vom Rhein an die Riviera. Jede Etappe hat ihre eigene Seite '
                  f'mit Karte, Höhenprofil, Übernachtung, Zusammenfassung und Fotos. '
                  f'Der höchste Punkt liegt auf Tag {highest["no"]} bei {metres(highest["maxEleM"])}.'),
        "stats": "".join([
            stat("Distanz", km(total_km)),
            stat("Aufstieg", metres(total_up, "+"), "value-up"),
            stat("Abstieg", metres(total_down, "-"), "value-down"),
            stat("Höchster Punkt", metres(highest["maxEleM"])),
        ]),
        "cards": "".join(cards),
        "pass_panel": panel,
    })
    assert_filled("stages.html", body)
    return page(
        trip, body,
        title=f'Etappen — {trip["title"]}',
        description=(f'Alle {len(stages)} Etappen von {stages[0]["from"]} nach {stages[-1]["to"]}: '
                     f'{km(total_km)}, {metres(total_up, "+")}, {pass_count} Pässe.'),
        extra_css='<link rel="stylesheet" href="assets/css/site.css">',
        scripts="", active="stages",
    )


# --- one stage -------------------------------------------------------------

def stars(rating):
    full = "★" * int(rating)
    empty = "☆" * (5 - int(rating))
    return f'<span class="stars" title="{rating} von 5">{full}<span class="off">{empty}</span></span>'


def lodging_block(stage):
    lodging = stage.get("lodging")
    if not lodging:
        return ('<!-- Add to data/trip.json: "lodging": {"name":…, "type":…, "place":…,'
                ' "url":…, "lat":…, "lon":…, "priceEur":…, "rating":…, "eleM":…, "note":…} -->\n'
                '<p class="empty-note">Für diesen Tag ist noch keine Übernachtung eingetragen.</p>')

    name = e(lodging["name"])
    if lodging.get("url"):
        name = f'<a href="{e(lodging["url"])}" target="_blank" rel="noopener">{name}</a>'

    figures = []
    if lodging.get("priceEur") is not None:
        figures.append(stat("Preis", f'{number(lodging["priceEur"])} €'))
    if lodging.get("rating"):
        figures.append(f'<div><dt>Bewertung</dt><dd>{stars(lodging["rating"])}</dd></div>')
    if lodging.get("eleM"):
        figures.append(stat("Höhe", metres(lodging["eleM"])))

    parts = ['<div class="lodging-card">', '<div class="lodging-head">', f"<h3>{name}</h3>"]
    if lodging.get("type"):
        parts.append(f'<span class="type-badge">{e(lodging["type"])}</span>')
    parts.append("</div>")
    if lodging.get("place"):
        parts.append(f'<p class="lodging-place">{e(lodging["place"])}</p>')
    if lodging.get("note"):
        parts.append(f'<p class="lodging-note">{e(lodging["note"])}</p>')
    if figures:
        parts.append(f'<dl class="stats lodging-figures">{"".join(figures)}</dl>')
    parts.append("</div>")

    if lodging.get("lat") and lodging.get("lon"):
        parts.append('<p class="lodging-hint">'
                     'Auf der Karte oben ist die Übernachtung mit einer Fahne markiert.</p>')
    return f'<div class="lodging">{"".join(parts)}</div>'


def summary_block(stage):
    paragraphs = stage.get("summary") or []
    if not paragraphs:
        return ('<!-- Add to data/trip.json: "summary": ["Erster Absatz", "Zweiter Absatz"] -->\n'
                '<p class="empty-note">Die Zusammenfassung zu diesem Tag fehlt noch.</p>')
    return '<div class="summary">' + "".join(f"<p>{e(p)}</p>" for p in paragraphs) + "</div>"


def photo_block(stage):
    photos = stage.get("photos") or []
    folder = f'photos/{stage["id"]}'
    if not photos:
        return (f'<!-- Put images in {folder}/, build thumbs with tools/prepare_photos.py,\n'
                f'     then in data/trip.json: "photos": [{{"file": "img-1234.jpg", "caption": "…"}}] -->\n'
                f'<p class="empty-note">Für diesen Tag sind noch keine Fotos eingepflegt.</p>')
    buttons = []
    for photo in photos:
        caption = e(photo.get("caption", ""))
        buttons.append(
            f'<li><button type="button" data-full="{folder}/{e(photo["file"])}"'
            f' data-caption="{caption}">'
            f'<img src="{folder}/thumbs/{e(photo["file"])}" alt="{caption}"'
            f' loading="lazy" decoding="async"></button></li>')
    return f'<ul class="photo-grid" id="photoGrid">{"".join(buttons)}</ul>'


def render_day(trip, stage, stages):
    no = stage["no"]
    neighbours = []
    if no > 1:
        previous = stages[no - 2]
        neighbours.append(f'<a class="prev" href="{previous["id"]}.html">'
                          f'<span class="direction">← Tag {previous["no"]}</span>'
                          f'<span class="target">{e(stage_name(previous))}</span></a>')
    if no < len(stages):
        following = stages[no]
        neighbours.append(f'<a class="next" href="{following["id"]}.html">'
                          f'<span class="direction">Tag {following["no"]} →</span>'
                          f'<span class="target">{e(stage_name(following))}</span></a>')

    strip = "".join(
        f'<a href="{s["id"]}.html"'
        + (' aria-current="page"' if s["id"] == stage["id"] else "")
        + f'><span class="index">Tag {s["no"]}</span>'
          f'<span class="place">{e(s["to"])}</span>'
          f'<span class="km">{km(s["distanceKm"])}</span></a>'
        for s in stages)

    passes = pass_chips(stage["passes"]) or (
        f'<span class="chip-empty">Geplant: {e(", ".join(stage["plannedPasses"]))}</span>'
        if stage["plannedPasses"] else '<span class="chip-empty">keine</span>')
    photos = stage.get("photos") or []

    body = fill((TEMPLATES / "day.html").read_text(encoding="utf-8"), {
        "no": str(no),
        "count": str(len(stages)),
        "date": e(long_date(stage["date"])),
        "from": e(stage["from"]),
        "to": e(stage["to"]),
        "gap": (f'<p class="day-gap"><b>Lücke im Track:</b> {e(stage["gap"])}</p>'
                if stage.get("gap") else ""),
        "stats": "".join([
            stat("Distanz", km(stage["distanceKm"])),
            stat("Aufstieg", metres(stage["ascentM"], "+"), "value-up"),
            stat("Abstieg", metres(stage["descentM"], "-"), "value-down"),
            stat("Höhe", f'{number(stage["minEleM"])}–{number(stage["maxEleM"])} m'),
            stat("Pässe", str(len(stage["passes"])) if stage["passes"] else "—"),
        ]),
        "pass_label": "Pass" if len(stage["passes"]) == 1 else "Pässe",
        "passes": passes,
        "strava": strava_chips(stage),
        "profile_label": e(f'{number(stage["minEleM"])} bis {number(stage["maxEleM"])} Meter, '
                           f'insgesamt {metres(stage["ascentM"], "+")} auf {km(stage["distanceKm"])}'),
        "lodging": lodging_block(stage),
        "summary": summary_block(stage),
        "photo_count": f'<span class="photo-count">{len(photos)}</span>' if photos else "",
        "photos": photo_block(stage),
        "neighbours": "".join(neighbours),
        "strip": strip,
    })
    assert_filled(f'{stage["id"]}.html', body)

    lodging = stage.get("lodging") or {}
    marker = None
    if lodging.get("lat") and lodging.get("lon"):
        marker = {
            "pos": [lodging["lat"], lodging["lon"]],
            "html": f'<b>{lodging["name"]}</b>'
                    + (f'{lodging.get("type", "")} · Übernachtung Tag {no}').strip(" ·"),
        }
    meta = {"id": stage["id"], "from": stage["from"], "to": stage["to"], "lodging": marker}
    scripts = (
        '<script src="assets/vendor/leaflet/leaflet.js"></script>\n'
        '<script src="assets/js/format.js"></script>\n'
        '<script src="assets/js/map.js"></script>\n'
        '<script src="assets/js/profile.js"></script>\n'
        '<script src="assets/js/lightbox.js"></script>\n'
        f'<script>window.RGA_STAGE={json.dumps(meta, ensure_ascii=False)};</script>\n'
        '<script src="assets/js/day.js"></script>'
    )
    description = (f'Tag {no} von {len(stages)} auf der Route des Grandes Alpes: '
                   f'{stage_name(stage)}, {km(stage["distanceKm"])} und '
                   f'{metres(stage["ascentM"], "+")}'
                   + (f' über {", ".join(p["name"] for p in stage["passes"])}.'
                      if stage["passes"] else "."))
    return page(
        trip, body,
        title=f'Tag {no}: {stage_name(stage)} — {trip["title"]}',
        og_title=f'Tag {no}: {stage_name(stage)}',
        description=description,
        extra_css=('<link rel="stylesheet" href="assets/css/site.css">\n'
                   '<link rel="stylesheet" href="assets/css/day.css">\n'
                   '<link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css">'),
        scripts=scripts, active="stages",
    )


# --- packing list ----------------------------------------------------------

def group_anchor(name):
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", " ": "-", "&": "und"})
    slug = "".join(c for c in name.lower().translate(table) if c.isalnum() or c == "-")
    return "group-" + slug.strip("-")


def render_packing_list(trip, stages, packing):
    totals = []
    luggage = 0
    for i, group in enumerate(packing["groups"]):
        colour = GROUP_COLOURS[i % len(GROUP_COLOURS)]
        weight = sum(item["qty"] * item["grams"] for item in group["items"])
        totals.append((group, colour, weight))
        if not group.get("wornOnBody"):
            luggage += weight

    groups_html, legend, split, jump = [], [], [], []
    for group, colour, weight in totals:
        rows = []
        for item in group["items"]:
            item_id = f'{group["name"]}|{item["name"]}'
            total = item["qty"] * item["grams"]
            verdict = ""
            if item.get("takeAgain") is True:
                verdict = '<span class="pack-verdict yes">wieder dabei</span>'
            elif item.get("takeAgain") is False:
                verdict = '<span class="pack-verdict no">bleibt daheim</span>'
            qty = f'<span class="pack-qty">×{item["qty"]}</span>' if item["qty"] > 1 else ""
            rows.append(
                f'<li class="pack-row">'
                f'<input type="checkbox" id="{e(item_id)}" data-id="{e(item_id)}" data-grams="{total}">'
                f'<label for="{e(item_id)}"><span class="pack-name">{e(item["name"])}</span>'
                f'{qty}{verdict}</label>'
                f'<span class="pack-weight">{grams(total)}</span>'
                + (f'<p class="pack-note">{e(item["note"])}</p>' if item.get("note") else "")
                + '</li>')
        groups_html.append(
            f'<section class="pack-group" id="{group_anchor(group["name"])}">'
            f'<div class="pack-group-head">'
            f'<h3><i style="background:{colour}"></i>{e(group["name"])}</h3>'
            f'<span class="pack-group-weight">{grams(weight)} · {len(group["items"])} Posten</span>'
            + (f'<p class="pack-group-note">{e(group["note"])}</p>' if group.get("note") else "")
            + f'</div><ul class="pack-list">{"".join(rows)}</ul></section>')
        jump.append(f'<a href="#{group_anchor(group["name"])}">{e(group["name"])}'
                    f'<b>{grams(weight)}</b></a>')
        if not group.get("wornOnBody"):
            split.append(f'<i style="background:{colour}; width:{weight / luggage * 100:.2f}%"'
                         f' title="{e(group["name"])}: {grams(weight)}"></i>')
            legend.append(f'<div><i style="background:{colour}"></i>{e(group["name"])}'
                          f'<b>{grams(weight)}</b></div>')

    worn = sum(w for group, _, w in totals if group.get("wornOnBody"))
    luggage_groups = len([g for g, _, _ in totals if not g.get("wornOnBody")])
    note = [f"in {luggage_groups} Gruppen, inkl. Rad"]
    if worn:
        note.append(f"am Körper zusätzlich {grams(worn)}")
    for base in packing.get("baseWeights") or []:
        note.append(f'{base["name"]}: {grams(base["grams"])}')

    value, unit = grams(luggage).split(" ")
    body = fill((TEMPLATES / "packing-list.html").read_text(encoding="utf-8"), {
        "eyebrow": (f'{e(stages[0]["from"])} → {e(stages[-1]["to"])} · '
                    f'{e(date_range(stages[0]["date"], stages[-1]["date"]))}'),
        "intro": e(packing.get("intro", "")),
        "total": value,
        "total_unit": unit,
        "total_note": e(" · ".join(note)),
        "split": "".join(split),
        "split_legend": "".join(legend),
        "jump_links": "".join(jump),
        "groups": "".join(groups_html),
    })
    assert_filled("packing-list.html", body)
    return page(
        trip, body,
        title=f'Packliste — {trip["title"]}',
        description=(f'Was auf {km(sum(s["distanceKm"] for s in stages))} von {stages[0]["from"]} '
                     f'nach {stages[-1]["to"]} mitfuhr: {grams(luggage)} Gepäck in '
                     f'{len(packing["groups"])} Gruppen, mit Gewichten und Fazit.'),
        extra_css='<link rel="stylesheet" href="assets/css/site.css">',
        scripts=('<script src="assets/js/format.js"></script>\n'
                 '<script src="assets/js/packing-list.js"></script>'),
        active="packing",
    )


# --- main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build the site from gpx/ and data/.")
    parser.add_argument("--check", action="store_true",
                        help="write nothing, just report which files are out of date")
    parser.add_argument("--smoothing", type=int, default=gpx.SMOOTHING_WINDOW_M, metavar="METRES",
                        help=f"average elevation over a window of METRES (default {gpx.SMOOTHING_WINDOW_M}, 0 = off)")
    args = parser.parse_args()

    trip, stages, tracks = load_stages(args.smoothing)
    packing = json.loads((DATA / "packing-list.json").read_text(encoding="utf-8"))

    files = {
        "index.html": render_home(trip, stages),
        "stages.html": render_stages(trip, stages),
        "packing-list.html": render_packing_list(trip, stages, packing),
    }
    for stage in stages:
        files[f'{stage["id"]}.html'] = render_day(trip, stage, stages)

    for sid, track in tracks.items():
        files[f"data/tracks/{sid}.json"] = json.dumps(
            track, ensure_ascii=False, separators=(",", ":")) + "\n"
    files["data/overview.json"] = json.dumps(
        [{"id": s["id"], "no": s["no"],
          "points": [[round(p["lat"], 5), round(p["lon"], 5)]
                     for p in gpx.every_nth(s["points"], gpx.MAX_OVERVIEW_POINTS)]}
         for s in stages],
        ensure_ascii=False, separators=(",", ":")) + "\n"

    stale = []
    for name, text in sorted(files.items()):
        target = ROOT / name
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == text:
            continue
        stale.append(name)
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    if args.check:
        if stale:
            print("Out of date: " + ", ".join(stale))
            sys.exit(1)
        print(f"All {len(files)} files are up to date.")
        return

    total_km = sum(s["distanceKm"] for s in stages)
    print(f'{len(stages)} stages, {total_km:.0f} km, '
          f'{sum(s["rawPoints"] for s in stages)} GPX points read')
    print(f"{len(files)} files checked, {len(stale)} written")
    for name in stale:
        print(f"  {name}  {(ROOT / name).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Piping into head/less closes stdout early; that is not an error.
        sys.stdout = None
