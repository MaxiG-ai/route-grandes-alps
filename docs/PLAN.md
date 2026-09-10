# Plan: von einer HTML-Datei zur Reise-Website

Ziel: Die bestehende Funktionalität (Etappenliste, Leaflet-Karte, Höhenprofil,
Pass-Chips, Strava-Links, Fortschritt) bleibt vollständig erhalten. Neu dazu
kommen Startseite, Packliste sowie pro Tag *Übernachtung*, *Zusammenfassung*
und *Fotos*. Sprache: Deutsch. Optik: Trikolore-Akzente auf Weiß.

## 1. Ausgangslage

`index.html` (537 Zeilen, 430 KB):

| Teil | Umfang | Bemerkung |
|---|---|---|
| `ROUTES` (Zeile 219) | **429 KB in einer Zeile** | 14 Tage × 310–800 Trackpunkte (`lat/lon/ele/d`) + Waypoints + Strava + Cols |
| `GAPS`, `PASSES`, `QD_PROFILE` | ~1,5 KB | handgepflegte Inhalte |
| CSS | ~250 Zeilen | Tokens, App-Shell, Sidebar, Karte, Profil, Dark Mode |
| JS | ~340 Zeilen | Leaflet, SVG-Profil, Sparklines, Sidebar, Init |

Die Trackdaten sind also 99 % des Gewichts. Genau daran hängt die
Struktur­entscheidung: Startseite und Packliste dürfen nicht 480 KB Geometrie
laden, und eine Etappe braucht nur ihren eigenen Track (~30 KB).

## 2. Struktur­entscheidung

**Empfehlung: statische Multi-Page-Site ohne Build-Schritt.** Getrennte
Dateien für CSS/JS/Daten, aber weiterhin nur HTML + Vanilla-JS, direkt auf
GitHub Pages deploybar. Kein npm, kein Bundler, kein Framework.

Warum nicht die Alternativen:

- *Alles in einer Datei lassen*: mit Startseite, Packliste, 14 Tages­texten und
  Foto-Manifesten wachsen wir auf ~600 KB und >1500 Zeilen in einer Datei —
  jeder Tippfehler im Tagestext riskiert die ganze Seite.
- *Build-Setup (Vite/Eleventy)*: bessere Templates, aber Toolchain, Node-Version,
  Deploy-Workflow. Für 3 Seiten überdimensioniert.
- *14 statische Tages­seiten*: bestes Teilen/SEO, aber 14 fast identische Dateien
  ohne Generator — Wartungsfalle. (Siehe Entscheidung D.)

### Dateibaum

```
/
├── index.html              Startseite
├── etappen.html            Etappen-Explorer (Karte + Profil + Tagesinhalte)
├── packliste.html          Packliste
├── .nojekyll               GitHub Pages: assets/ nicht durch Jekyll filtern
├── assets/
│   ├── css/
│   │   ├── base.css        Farb-Tokens (Trikolore), Typografie, Grundraster
│   │   ├── site.css        Header/Footer, Startseite, Packliste
│   │   └── etappen.css     App-Shell, Sidebar, Karte, Profil, Lightbox
│   ├── js/
│   │   ├── format.js       de-DE Datum/Zahlen, statusOf(), dayNo(), fmtKm()
│   │   ├── reise.js        lädt data/reise.json, Helfer (Tage, Summen, Pässe)
│   │   ├── karte.js        Leaflet-Setup, Layer-Umschalter, renderRoute()
│   │   ├── profil.js       SVG-Höhenprofil + Hover-Cursor
│   │   ├── etappenliste.js Sidebar-Karten + Sparklines
│   │   ├── lightbox.js     Foto-Galerie (Tastatur, Swipe, lazy)
│   │   ├── etappen.js      Seiten-Controller + Hash-Routing (#tag-7)
│   │   ├── start.js        Startseite: Summen, Übersichtskarte, Fortschritt
│   │   └── packliste.js    Rendern, Gewichtssummen, Häkchen (localStorage)
│   └── vendor/leaflet/     Leaflet 1.9.4 lokal (statt unpkg-CDN)
├── data/
│   ├── reise.json          Reise-Meta + 14× Etappen-Meta, Übernachtung,
│   │                       Zusammenfassung, Pässe, Strava, Foto-Manifest
│   ├── packliste.json      Kategorien → Gegenstände (Gewicht, Anzahl, Notiz)
│   ├── uebersicht.json     ausgedünnte Geometrie aller 14 Tage (~30 KB)
│   └── tracks/tag-01.json … tag-14.json   generiert: points + waypoints
├── fotos/
│   └── tag-01/  bild.jpg + thumbs/bild.jpg   (pro Tag ein Ordner)
├── tools/
│   ├── gpx_to_track.py     GPX → data/tracks/*.json + uebersicht.json
│   └── fotos_vorbereiten.py  skalieren, Thumbs, Manifest-Gerüst
└── README.md               lokal starten, Tag ergänzen, Fotos einpflegen
```

### Trennung: generierte Geometrie vs. handgeschriebener Inhalt

Wichtigste Regel des Umbaus: **`data/tracks/*.json` ist maschinen­erzeugt und
jederzeit überschreibbar**, `data/reise.json` ist handgepflegt. Läge die Prosa
in derselben Datei wie der Track, würde jedes GPX-Neuerzeugen die Texte
zerschießen.

`data/reise.json` (Auszug):

```json
{
  "titel": "Rhein bis Riviera",
  "untertitel": "Karlsruhe → Isolabona · 30. Aug – 12. Sep 2026",
  "stravaProfil": "https://www.strava.com/athletes/11965636",
  "etappen": [{
    "id": "tag-07",
    "nr": 7,
    "von": "Beaufort", "nach": "Séez",
    "datum": "2026-09-05",
    "distanzKm": 54.6, "aufstiegM": 1512, "abstiegM": 1104,
    "minHoehe": 745, "maxHoehe": 1968,
    "luecke": null,
    "cols": ["Cormet de Roselend"],
    "paesse": [{ "name": "Cormet de Roselend", "hoehe": 1968,
                 "url": "https://www.quaeldich.de/paesse/cormet-de-roselend/",
                 "manuell": true }],
    "strava": [{ "id": "…", "name": "RGA Tag 7", "distanzKm": 54.6, "aufstiegM": 1512 }],
    "uebernachtung": {
      "name": "Camping Le Reclard", "art": "Camping",
      "ort": "Séez", "url": null, "lat": 45.62, "lon": 6.80,
      "preisEur": 14, "bewertung": 4,
      "notiz": "Heiße Duschen, Bäcker 300 m bergab."
    },
    "zusammenfassung": [
      "Erster Absatz …",
      "Zweiter Absatz …"
    ],
    "fotos": [
      { "datei": "img_0421.jpg", "titel": "Stausee von Roselend im Gegenlicht" }
    ]
  }]
}
```

Die Foto-Pfade ergeben sich aus Konvention (`fotos/tag-07/…` und
`fotos/tag-07/thumbs/…`), damit das Manifest kurz bleibt. Distanz-/Höhenwerte
bleiben redundant in `reise.json`, damit Startseite und Sidebar ohne
Track-Download rechnen können — `tools/gpx_to_track.py` schreibt sie mit.

## 3. Seiten im Detail

### `index.html` — Startseite

- Hero: Titel, Route, Zeitraum, Trikolore-Kante; ein großes Foto.
- Kennzahlen aus `reise.json`: Gesamtdistanz (~2.100 km), Höhenmeter,
  Pässe, gefahrene km, Fortschrittsbalken (die bestehende `statusOf()`-Logik
  gegen das heutige Datum).
- Übersichtskarte: alle 14 Etappen aus `uebersicht.json`, Klick → `etappen.html#tag-n`.
- Drei Einstiegskarten: *Etappen*, *Packliste*, *Fotos*.
- Etappen-Tabelle (Tag, Datum, Von → Nach, km, hm, Pässe) als Sprungliste.

### `etappen.html` — der bestehende Explorer, erweitert

Bleibt eine Datei mit Hash-Routing (`#tag-7`), damit ein Tag verlinkbar ist,
ohne 14 HTML-Kopien zu pflegen. Layout-Änderung: die Seite scrollt jetzt.

1. Sidebar: unverändert (Karten mit Sparkline, Datum, Status, Pass-Panel).
2. Kartenblock: Leaflet + Höhenprofil, feste Höhe (~60 vh, Vollbild-Knopf),
   Statistikleiste, Layer-Umschalter, Pass-Chips, Strava — **wie heute**.
3. **Neu: Übernachtung** — Karte mit Name, Art, Preis, Bewertung, Notiz,
   Link und Mini-Pin.
4. **Neu: Zusammenfassung** — Absätze aus `reise.json`, ruhige Lesespalte
   (max. 68 Zeichen), darüber die Tageseckdaten als Kurzfassung.
5. **Neu: Fotos** — responsives Raster aus Thumbs, `loading="lazy"`,
   Klick öffnet eine selbst gebaute Lightbox (Pfeiltasten, Escape, Swipe,
   Bildtitel). Keine Fremdbibliothek nötig (~70 Zeilen).

Nur der gerade gewählte Tag lädt seinen Track (`data/tracks/tag-07.json`),
gecacht in einer Map — Erstaufruf damit ~40 KB statt 430 KB.

### `packliste.html`

Aus `data/packliste.json`: Kategorien (Fahrrad & Gepäck, Werkzeug, Schlafen,
Kleidung, Küche, Elektronik, Papiere, Erste Hilfe), je Gegenstand Anzahl,
Gramm, Notiz und ein Feld `wiederMitnehmen: true|false|null` für das Fazit
nach der Reise. Die Seite rechnet Gewicht je Kategorie und Gesamtgewicht,
zeigt einen Balken pro Kategorie und speichert Häkchen zum Abpacken in
`localStorage`.

## 4. Deutsch

- `<html lang="de">`, alle UI-Strings im Markup bzw. in `format.js` gebündelt.
- Datum: `toLocaleDateString('de-DE', { weekday:'short', day:'numeric', month:'short' })`
  → „So., 5. Sep.“
- Zahlen: `toLocaleString('de-DE')` → „1.512 m“ (Punkt als Tausendertrenner),
  Komma als Dezimaltrenner bei km.
- Begriffe: Etappen, Tag 7 von 14, Packliste, Übernachtung, Zusammenfassung,
  Fotos, Pässe, Distanz, Aufstieg, Abstieg, Höhe, Gelände/Straßen,
  „heute“, „noch nicht gefahren“, „Lücke im Track“.

## 5. Farben (Trikolore auf Weiß)

Tokens in `base.css`, Dark-Mode-Blöcke entfallen (`color-scheme: light`):

```css
:root{
  --blanc:#ffffff;          /* Seitengrund */
  --papier:#f6f7fa;         /* Flächen, Sidebar */
  --linie:#dfe4ee;
  --bleu:#0055a4;           /* Primär, Links, aktive Etappe */
  --bleu-tief:#003d78;      /* Text auf Weiß, Hover */
  --rouge:#ef4135;          /* Akzent, Flächen, Marker */
  --rouge-tief:#c8102e;     /* roter Text auf Weiß (Kontrast) */
  --ink:#111827; --ink-soft:#4a5568; --ink-faint:#7b859b;
}
```

Kontrast-Hinweis: `#ef4135` auf Weiß erreicht nur ~3,6:1 — deshalb Rot nur
für Flächen, Kanten und Marker; roter **Text** nutzt `--rouge-tief` (~5,9:1).
Die Trikolore-Kante (blau/weiß/rot) taucht als 3-px-Leiste im Header, an
Hero-Kanten und als Trenner zwischen Tages-Abschnitten auf.

Angenehmer Nebeneffekt: die hypsometrische Rampe des Höhenprofils ist heute
schon Blau → Weiß → Rot und passt unverändert.

## 6. Umbau in Etappen

| # | Schritt | Ergebnis |
|---|---|---|
| 1 | Extraktion: CSS/JS/Daten aus `index.html` in die Struktur oben, `etappen.html` bekommt die heutige App 1:1, Tracks per Skript nach `data/tracks/` | Funktions­gleichheit, nachweisbar per Vergleich |
| 2 | Retheming Trikolore + Deutsch (`lang`, Strings, `de-DE`-Formate), Dark Mode raus | Optik und Sprache fertig |
| 3 | `index.html` Startseite + `uebersicht.json` | Landing steht |
| 4 | `packliste.html` + `data/packliste.json` | Packliste steht |
| 5 | Übernachtung + Zusammenfassung: Felder in `reise.json`, Abschnitte in `etappen.html` | zwei neue Abschnitte pro Tag |
| 6 | Fotos: Ordner, `fotos_vorbereiten.py`, Raster + Lightbox | Fotos pro Tag |
| 7 | `README.md`, `.nojekyll`, Pages aktivieren | dokumentiert und live |

Schritt 1 ist reines Verschieben — dort wird nichts umbenannt oder
verbessert, damit ein Fehler später eindeutig einem Schritt zuzuordnen ist.

## 7. Offene Punkte / Kompromisse

- **`fetch()` braucht einen Server.** Per Doppelklick aus dem Dateisystem
  (`file://`) blockiert der Browser JSON-Ladevorgänge — heute funktioniert die
  eine Datei offline. Lokal also `python3 -m http.server`. Wer den
  Doppelklick behalten will, legt die Daten als klassische
  `data/tracks/tag-07.js` mit `window.RGA_TRACK = {…}` ab; das lädt auch von
  `file://`, ist aber unschöner.
- **Fotogröße.** Empfehlung: im Repo nur skaliert (max. 1600 px, Qualität 80,
  ~250 KB) plus Thumbs (400 px, ~35 KB). 14 Tage × 10 Bilder ≈ 40 MB — für
  Git und Pages (1 GB Limit) in Ordnung, Originale bleiben außerhalb.
- **Leaflet lokal statt CDN**: 150 KB im Repo, dafür kein Fremd-Ausfall und
  offline nutzbar.
- **Fotos-Gesamtgalerie** über alle Tage: leicht nachzurüsten, sobald die
  Manifeste stehen — vorerst nicht eingeplant.
