# Plan: von einer HTML-Datei zur Reise-Website

Ziel: Die bestehende Funktionalität (Etappenliste, Leaflet-Karte, Höhenprofil,
Pass-Chips, Strava-Links, Fortschritt) bleibt vollständig erhalten. Neu dazu
kommen Startseite, Packliste sowie pro Tag *Übernachtung*, *Zusammenfassung*
und *Fotos*. Sprache: Deutsch. Optik: Trikolore-Akzente auf Weiß.

## 1. Ausgangslage

`reference/index-original.html` (537 Zeilen, 430 KB):

| Teil | Umfang | Bemerkung |
|---|---|---|
| `ROUTES` (Zeile 219) | **429 KB in einer Zeile** | 14 Tage × 310–800 Trackpunkte (`lat/lon/ele/d`) + Waypoints + Strava + Cols |
| `GAPS`, `PASSES`, `QD_PROFILE` | ~1,5 KB | handgepflegte Inhalte |
| CSS | ~250 Zeilen | Tokens, App-Shell, Sidebar, Karte, Profil, Dark Mode |
| JS | ~340 Zeilen | Leaflet, SVG-Profil, Sparklines, Sidebar, Init |

Die Trackdaten sind also 99 % des Gewichts. Genau daran hängt die
Struktur­entscheidung: Startseite und Packliste dürfen nicht 480 KB Geometrie
laden, und eine Etappe braucht nur ihren eigenen Track (~30 KB).

## 2. Getroffene Entscheidungen

| Frage | Entscheidung |
|---|---|
| Tages-Seiten | **14 statische Seiten** `tag-01.html … tag-14.html`, erzeugt von `tools/build_tage.py` aus einem Template + `data/reise.json` |
| Datenladen | `fetch()` + JSON — das Hosting liefert über HTTP aus, kein `file://`-Zwang |
| Hosting | **Hetzner Webhosting**, reiner Datei-Upload, `index.html` im Wurzelverzeichnis, ausschließlich relative Pfade |
| Fotos | im Repo, skaliert (max. 1600 px) + 400-px-Thumbs |
| Sprache | nur Deutsch |

Kein Build-Schritt zur Laufzeit, kein npm, kein Framework: `tools/build_tage.py`
läuft lokal, sein Ergebnis wird eingecheckt und mit hochgeladen. Was auf dem
Server liegt, ist fertiges HTML.

## 3. Struktur

Statische Multi-Page-Site, weiter reines HTML + Vanilla-JS + Leaflet.

```
/
├── index.html              Startseite
├── etappen.html            Übersicht aller 14 Etappen (Liste + Übersichtskarte)
├── tag-01.html … tag-14.html   generiert: Karte, Profil, Übernachtung,
│                               Zusammenfassung, Fotos
├── packliste.html          Packliste
├── assets/
│   ├── css/
│   │   ├── base.css        Farb-Tokens (Trikolore), Typografie, Grundraster
│   │   ├── site.css        Header/Footer, Startseite, Etappenübersicht, Packliste
│   │   └── tag.css         Kartenblock, Sidebar, Profil, Fotoraster, Lightbox
│   ├── js/
│   │   ├── format.js       de-DE Datum/Zahlen, statusOf(), fmtKm()
│   │   ├── karte.js        Leaflet-Setup, Layer-Umschalter, renderRoute()
│   │   ├── profil.js       SVG-Höhenprofil + Hover-Cursor
│   │   ├── sparkline.js    Mini-Profile für die Etappenkarten
│   │   ├── lightbox.js     Foto-Galerie (Pfeiltasten, Escape, Swipe)
│   │   ├── tag.js          Controller einer Tages-Seite
│   │   ├── start.js        Startseite: Summen, Übersichtskarte, Fortschritt
│   │   └── packliste.js    Rendern, Gewichtssummen, Häkchen (localStorage)
│   └── vendor/leaflet/     Leaflet 1.9.4 lokal statt unpkg-CDN
├── data/
│   ├── reise.json          Reise-Meta + 14× Etappen-Meta, Übernachtung,
│   │                       Zusammenfassung, Pässe, Strava, Foto-Manifest
│   ├── packliste.json      Kategorien → Gegenstände (Gewicht, Anzahl, Notiz)
│   ├── uebersicht.json     ausgedünnte Geometrie aller 14 Tage (~30 KB)
│   └── tracks/tag-01.json … tag-14.json   generiert: points + waypoints
├── fotos/
│   └── tag-01/  bild.jpg + thumbs/bild.jpg   (pro Tag ein Ordner)
├── templates/
│   ├── tag.html            Vorlage für die Tages-Seiten
│   └── _kopf.html          Header/Footer-Bausteine für den Generator
├── tools/
│   ├── gpx_to_track.py     GPX → data/tracks/*.json + uebersicht.json
│   ├── fotos_vorbereiten.py  skalieren, Thumbs, Manifest-Gerüst
│   └── build_tage.py       templates + reise.json → tag-NN.html
├── reference/index-original.html   Ausgangsdatei als Vergleichsbasis
└── README.md               lokal starten, Tag ergänzen, Fotos, Upload
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
    "zusammenfassung": ["Erster Absatz …", "Zweiter Absatz …"],
    "fotos": [{ "datei": "img_0421.jpg", "titel": "Stausee von Roselend im Gegenlicht" }]
  }]
}
```

Foto-Pfade ergeben sich aus Konvention (`fotos/tag-07/…` bzw.
`fotos/tag-07/thumbs/…`), damit das Manifest kurz bleibt. Distanz- und
Höhenwerte stehen redundant in `reise.json`, damit Startseite und Sidebar
ohne Track-Download rechnen können — `tools/gpx_to_track.py` schreibt sie mit.

### Der Generator

`tools/build_tage.py` füllt `templates/tag.html` pro Etappe. Kein
Template-Framework: Platzhalter `{{titel}}`, `{{datum}}`, `{{fotoraster}}` &
Co. werden per `str.replace` ersetzt.

Bewusst **vorgerendert ins HTML** (funktioniert damit auch ohne JavaScript und
liefert echten Seitentitel, `<meta description>` und Vorschaubild pro Tag):
Kopfzeile, Eckdaten, Pass-Chips, Strava-Links, Übernachtung, Zusammenfassung,
Fotoraster, Vor/Zurück-Navigation und die Etappen-Sidebar.

Per JavaScript bleiben nur die interaktiven Teile: Leaflet-Karte,
Höhenprofil (lädt `data/tracks/tag-07.json`, ~30 KB) und Lightbox.

Der Generator ist idempotent: `python3 tools/build_tage.py` nach jeder
Änderung an `reise.json` oder am Template neu laufen lassen, Ergebnis
einchecken. Ein `--check`-Modus vergleicht nur und schlägt an, wenn eine
eingecheckte Seite veraltet ist.

## 4. Seiten im Detail

### `index.html` — Startseite

- Hero: Titel, Route, Zeitraum, Trikolore-Kante, ein großes Foto.
- Kennzahlen aus `reise.json`: Gesamtdistanz (~2.100 km), Höhenmeter, Pässe,
  gefahrene km, Fortschrittsbalken (bestehende `statusOf()`-Logik gegen das
  heutige Datum).
- Übersichtskarte: alle 14 Etappen aus `uebersicht.json`, Klick → `tag-NN.html`.
- Drei Einstiegskarten: *Etappen*, *Packliste*, *Fotos*.
- Etappen-Tabelle (Tag, Datum, Von → Nach, km, hm, Pässe) mit Links.

### `etappen.html` — Übersicht

Alle 14 Etappen als Karten mit Sparkline, Datum, Status („heute“, „noch nicht
gefahren“), Distanz/Höhenmetern und Pässen — die heutige Sidebar in groß,
plus das Pass-Panel („Gefahrene Pässe · 18“, verlinkt auf quäldich.de).

### `tag-NN.html` — eine Etappe

1. Kopf: „Tag 7 von 14 · So., 5. Sep.“, Von → Nach, Eckdaten, Lücken-Hinweis.
2. Kartenblock: Leaflet + Höhenprofil mit gekoppeltem Cursor, Layer-Umschalter
   (Gelände/Straßen), Start-/Ziel-Marker, Waypoint-Popups, Pass-Chips,
   Strava-Links — **funktional wie heute**, feste Höhe (~60 vh).
3. **Neu: Übernachtung** — Name, Art, Ort, Preis, Bewertung, Notiz, Link,
   Mini-Pin auf der Karte.
4. **Neu: Zusammenfassung** — Absätze aus `reise.json` in ruhiger Lesespalte
   (max. ~68 Zeichen Zeilenlänge).
5. **Neu: Fotos** — responsives Thumb-Raster, `loading="lazy"`, Klick öffnet
   eine selbst gebaute Lightbox (Pfeiltasten, Escape, Swipe, Bildtitel).
   Keine Fremdbibliothek, ~70 Zeilen.
6. Fuß: Vor/Zurück zur Nachbaretappe, Sidebar/Sprungliste aller Tage.

### `packliste.html`

Aus `data/packliste.json`: Kategorien (Fahrrad & Gepäck, Werkzeug, Schlafen,
Kleidung, Küche, Elektronik, Papiere, Erste Hilfe), je Gegenstand Anzahl,
Gramm, Notiz und ein Feld `wiederMitnehmen: true|false|null` für das Fazit
nach der Reise. Gewicht je Kategorie und Gesamtgewicht werden gerechnet,
ein Balken pro Kategorie zeigt die Verteilung, Häkchen zum Abpacken landen
in `localStorage`.

## 5. Deutsch

- `<html lang="de">`, alle UI-Strings im Markup bzw. gebündelt in `format.js`.
- Datum: `toLocaleDateString('de-DE', { weekday:'short', day:'numeric', month:'short' })`
  → „So., 5. Sep.“
- Zahlen: `toLocaleString('de-DE')` → „1.512 m“; Komma als Dezimaltrenner bei km.
- Begriffe: Etappen, Tag 7 von 14, Packliste, Übernachtung, Zusammenfassung,
  Fotos, Pässe, Distanz, Aufstieg, Abstieg, Höhe, Gelände/Straßen, „heute“,
  „noch nicht gefahren“, „Lücke im Track“.

## 6. Farben (Trikolore auf Weiß)

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

Kontrast-Hinweis: `#ef4135` erreicht auf Weiß nur ~3,6:1 — Rot deshalb nur
für Flächen, Kanten und Marker; roter **Text** nutzt `--rouge-tief` (~5,9:1).
Die Trikolore-Kante (blau/weiß/rot) erscheint als 3-px-Leiste im Header, an
Hero-Kanten und als Trenner zwischen den Tages-Abschnitten.

Angenehmer Nebeneffekt: die hypsometrische Rampe des Höhenprofils ist heute
schon Blau → Weiß → Rot und passt unverändert.

## 7. Hosting bei Hetzner

- Reiner Datei-Upload nach `/public_html` (bzw. dem Dokumentwurzel-Ordner):
  `index.html`, `etappen.html`, `tag-*.html`, `packliste.html`, `assets/`,
  `data/`, `fotos/`. Sonst nichts — `tools/`, `templates/`, `docs/`,
  `reference/` bleiben im Repo.
- **Nur relative Pfade** (`assets/css/base.css`, nicht `/assets/…`), damit die
  Site auch in einem Unterordner läuft.
- Apache liefert `.json` von sich aus aus; `fetch()` funktioniert also ohne
  Konfiguration. Kein `.htaccess` nötig — optional eine Zeile für
  Cache-Header auf `fotos/` und `assets/`.
- Optional `tools/upload.sh` mit `lftp`/`rsync` (Zugangsdaten aus der Umgebung,
  **nie** im Repo).
- Prüfen: nach dem Upload einmal `tag-07.html` direkt aufrufen — dort zeigt
  sich sofort, ob relative Pfade und `data/tracks/…` stimmen.

## 8. Umbau in Etappen

| # | Schritt | Ergebnis |
|---|---|---|
| 1 | Extraktion: CSS/JS aus der Ausgangsdatei in die Struktur oben, Tracks per Skript nach `data/tracks/`, `reise.json` aus `ROUTES`/`PASSES`/`GAPS` ableiten | eine Tages-Seite funktional gleich wie heute |
| 2 | `tools/build_tage.py` + `templates/tag.html`, alle 14 Seiten erzeugen, `etappen.html` als Übersicht | Navigation vollständig |
| 3 | Retheming Trikolore + Deutsch (`lang`, Strings, `de-DE`-Formate), Dark Mode raus | Optik und Sprache fertig |
| 4 | `index.html` Startseite + `uebersicht.json` | Landing steht |
| 5 | `packliste.html` + `data/packliste.json` | Packliste steht |
| 6 | Übernachtung + Zusammenfassung: Felder in `reise.json`, Abschnitte im Template | zwei neue Abschnitte pro Tag |
| 7 | Fotos: Ordner, `fotos_vorbereiten.py`, Raster + Lightbox | Fotos pro Tag |
| 8 | `README.md` (lokal starten, Tag ergänzen, Fotos, Upload), Feinschliff | dokumentiert und hochladbar |

Schritt 1 ist reines Verschieben — dort wird nichts umbenannt oder
verbessert, damit ein späterer Fehler eindeutig einem Schritt zuzuordnen ist.

## 9. Offene Punkte

- **Inhalte fehlen noch.** Übernachtungen, Zusammenfassungen und Fotos sind
  Handarbeit. Der Umbau legt die Felder an und füllt sie mit sichtbaren
  Platzhaltern (`"zusammenfassung": []` → Abschnitt wird ausgelassen), sodass
  jeder Tag nachträglich einzeln ergänzt werden kann.
- **Fotogröße.** 14 Tage × 10 Bilder ≈ 40 MB im Repo — vertretbar. Originale
  bleiben außerhalb; `fotos_vorbereiten.py` erzeugt die Web-Größen.
- **Leaflet lokal statt CDN**: 150 KB im Repo, dafür kein Fremd-Ausfall.
- **Fotos-Gesamtgalerie** über alle Tage: leicht nachrüstbar, sobald die
  Manifeste stehen — vorerst nicht eingeplant.
- **Lokal testen** trotz Hosting-Ziel: `python3 -m http.server` im
  Projektordner, dann `http://localhost:8000`.
