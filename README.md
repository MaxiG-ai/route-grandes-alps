# Rhein bis Riviera

Website zu meiner Bikepacking-Tour auf der Route des Grandes Alpes:
Karlsruhe → Isolabona, 14 Etappen, 30. August – 12. September 2026.

Statische Seiten, kein Framework, kein Build zur Laufzeit. Was im
Projektordner liegt, kann man so ins Webhosting hochladen.

```
index.html         Startseite: Kennzahlen, Übersichtskarte, Etappentabelle
etappen.html       alle Etappen als Karten, dazu die Liste der gefahrenen Pässe
tag-01 … tag-14    je eine Etappe: Karte, Höhenprofil, Übernachtung,
                   Zusammenfassung, Fotos
packliste.html     Packliste mit Gewichten und Fazit
```

Die HTML-Dateien sind **erzeugt** — nicht direkt bearbeiten, sondern
`data/` bzw. `templates/` ändern und neu bauen.

## Lokal ansehen

`fetch()` funktioniert nicht über `file://`, also einen kleinen Server starten:

```sh
python3 -m http.server 8000
# → http://localhost:8000
```

## Bauen

```sh
python3 tools/build.py            # alle 17 Seiten schreiben
python3 tools/build.py --check    # nur prüfen, ob die Dateien aktuell sind
python3 tools/build.py --heute 2026-09-05   # Stichtag für gefahren/heute/geplant
```

Der Reisestatus (gefahren · heute · geplant), der Fortschrittsbalken und der
Knopf „Etappe von heute“ werden **beim Bauen** gegen das Tagesdatum bestimmt.
Deshalb: vor dem Hochladen einmal neu bauen.

## Woher die Inhalte kommen

| Datei | Inhalt | Pflege |
|---|---|---|
| `data/reise.json` | Etappen-Eckdaten, Pässe, Strava, Übernachtung, Zusammenfassung, Fotoliste | **von Hand** |
| `data/packliste.json` | Packliste nach Gruppen | **von Hand** |
| `data/wegpunkte.json` | deutsche Namen für die Zwischenziele aus der komoot-Planung | **von Hand** |
| `data/tracks/tag-NN.json` | Trackpunkte und Wegpunkte einer Etappe (~30 KB, wird erst beim Öffnen der Etappe geladen) | erzeugt |
| `data/uebersicht.json` | ausgedünnte Geometrie aller Etappen für die Startseitenkarte | erzeugt |
| `fotos/tag-NN/` | Bilder in Webgröße plus `thumbs/` | erzeugt aus Originalen |

Die Trennung ist Absicht: Trackdateien darf jedes Skript überschreiben,
`data/reise.json` enthält handgeschriebenen Text. Deshalb rührt
`tools/gpx_to_track.py` nur die Zahlenfelder an.

### Eine Zusammenfassung schreiben

In `data/reise.json` bei der Etappe:

```json
"zusammenfassung": [
  "Erster Absatz.",
  "Zweiter Absatz."
]
```

Leere Liste = der Abschnitt zeigt einen dezenten Hinweis, dass der Text noch fehlt.

### Eine Übernachtung eintragen

```json
"uebernachtung": {
  "name": "Camping Le Reclard", "art": "Camping", "ort": "Séez",
  "url": null, "lat": 45.62, "lon": 6.80,
  "preisEur": 14, "bewertung": 4, "hoehe": 1050,
  "notiz": "Heiße Duschen, Bäcker 300 m bergab."
}
```

`lat`/`lon` sind optional — sind sie da, erscheint auf der Karte eine Fahne.
Alle anderen Felder dürfen fehlen oder `null` sein.

### Fotos einpflegen

```sh
python3 tools/fotos_vorbereiten.py tag-07 ~/Bilder/RGA/tag07/*.jpg
```

Skaliert auf max. 1600 px, baut 400-px-Thumbs, richtet gedrehte Handyfotos auf
und schreibt die Dateiliste nach `data/reise.json`. Die Bildtitel kommen von
Hand dazu (`"titel"`), sie sind `alt`-Text und Bildunterschrift in der Lightbox.
Braucht Pillow: `pip install Pillow`. Details in `fotos/README.md`.

### Zwischenziele umbenennen

Die Wegpunkte kommen englisch aus komoot (`Shaded Cycle Path`) und stecken in
den erzeugten Trackdateien. Übersetzt werden sie deshalb in
`data/wegpunkte.json`:

```json
"namen": { "Shaded Cycle Path": "Schattiger Radweg" }
```

Namen ohne Eintrag erscheinen unverändert — Eigennamen wie `Col de Vars` oder
`Edeka Kohler` brauchen also keinen. Die Tabelle überlebt jedes Neuerzeugen
der Tracks; ein Neubauen ist nicht nötig, die Karte liest sie zur Laufzeit.

### Eine Etappe hinzufügen oder einen Track ersetzen

```sh
python3 tools/gpx_to_track.py tag-15 ~/Downloads/etappe15.gpx --datum 2026-09-13 --von Isolabona --nach Ventimiglia
python3 tools/build.py
```

`tools/extract_original.py` hat die Daten einmalig aus der ursprünglichen
Einzeldatei (`reference/index-original.html`) gezogen. Es überschreibt
`data/reise.json` komplett und darf deshalb nicht mehr laufen, sobald dort
Texte stehen.

## Hochladen (Hetzner Webhosting)

Alle Pfade sind relativ, die Seite läuft also auch in einem Unterordner.
Hochgeladen werden nur:

```
index.html  etappen.html  packliste.html  tag-*.html
assets/  data/  fotos/  .htaccess
```

`tools/`, `templates/`, `docs/` und `reference/` bleiben lokal.

```sh
export RGA_HOST=…  RGA_USER=…  RGA_PFAD=/public_html
./tools/upload.sh --trocken   # erst zeigen lassen
./tools/upload.sh
```

Das Skript baut vorher `--check` ein, damit keine veraltete Seite hochgeht.
Wer per SFTP-Programm hochlädt: dieselbe Dateiliste, Zielordner ist das
Dokumentwurzel-Verzeichnis. `.htaccess` ist optional und setzt nur
Cache-Zeiten und Kompression.

Zur Kontrolle nach dem Upload eine Etappenseite direkt aufrufen
(`…/tag-07.html`) — dort zeigt sich sofort, ob `assets/` und
`data/tracks/` mitgekommen sind.

## Aufbau

```
assets/css/base.css     Farb-Tokens (Trikolore auf Weiß), Typografie, Kopf/Fuß
assets/css/site.css     Startseite, Etappenübersicht, Packliste
assets/css/tag.css      Etappenseite: Karte, Profil, Fotoraster, Lightbox
assets/js/format.js     deutsche Zahlen- und Datumsformate
assets/js/karte.js      Leaflet-Grundgerüst, Linien, Marker
assets/js/profil.js     Höhenprofil als SVG, Cursor gekoppelt an die Karte
assets/js/lightbox.js   Fotogalerie (Pfeiltasten, Escape, Wischen)
assets/js/tag.js        Etappenseite: Track laden, Karte und Profil zeichnen
assets/js/start.js      Übersichtskarte der Startseite
assets/js/packliste.js  Häkchen zum Abpacken (localStorage)
assets/vendor/leaflet/  Leaflet 1.9.4, lokal statt per CDN
templates/              Vorlagen für den Generator
docs/PLAN.md            Plan des Umbaus aus der ursprünglichen Einzeldatei
```

JavaScript ist nur für Karte, Höhenprofil, Lightbox und die Packlisten-Häkchen
zuständig. Alle Texte, Zahlen und Bildverweise stehen fest im HTML — ohne
JavaScript fehlen also nur die Karten.

Kartenkacheln kommen von OpenTopoMap und CARTO, Kartendaten von
OpenStreetMap. Pässe verlinken auf quäldich.de, Fahrten auf Strava.
