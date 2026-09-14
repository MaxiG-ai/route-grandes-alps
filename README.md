# Karlsruhe to Liguria

Website for a bikepacking trip along the Route des Grandes Alpes:
Karlsruhe → Isolabona, 14 stages, 30 August – 12 September 2026.

Static pages, no framework, nothing built at request time. Whatever sits in
the project folder can be uploaded to the web host as it is.

**The site is in German, the repository is in English.** Code, comments,
filenames, JSON keys and CLI flags are English; only the text a visitor
reads is German.

```
index.html          landing page: figures, overview map, stage table
stages.html         every stage as a card, plus the list of passes ridden
day-01 … day-14     one stage each: map, elevation profile, lodging,
                    summary, photos
packing-list.html   packing list with weights and a verdict per item
```

The HTML files are **generated** — do not edit them directly. Change
`gpx/`, `data/` or `templates/` and rebuild.

## Look at it locally

`fetch()` does not work over `file://`, so serve the folder:

```sh
python3 -m http.server 8000
# → http://localhost:8000
```

## Build

```sh
python3 tools/build.py                     # write all 32 output files
python3 tools/build.py --check             # only report what is out of date
python3 tools/build.py --today 2026-09-05  # pin the ridden/today/planned date
python3 tools/build.py --smoothing 0       # no elevation smoothing
```

The ridden · today · planned state, the progress bar and the "Etappe von
heute" button are worked out **at build time** from the current date. So
rebuild before uploading.

## Where the content comes from

| Path | Contains | Maintained |
|---|---|---|
| `gpx/day-NN.gpx` | one track per stage — the source for distance, ascent, descent, elevation range and the profile | **by hand** (dropped in) |
| `data/trip.json` | stage content: from, to, date, passes, Strava, lodging, summary, photo list | **by hand** |
| `data/packing-list.json` | the packing list by group | **by hand** |
| `data/waypoints.json` | German names for the komoot waypoints | **by hand** |
| `data/tracks/day-NN.json` | thinned geometry, fetched when a stage page opens | generated |
| `data/overview.json` | all stages thinned further, for the landing map | generated |
| `photos/day-NN/` | web-size images plus `thumbs/` | generated from originals |

Generated files are committed so that the repository matches what gets
uploaded, but they are never edited by hand.

### Adding or replacing a stage track

Drop the GPX file in as `gpx/day-NN.gpx` and rebuild:

```sh
cp ~/Downloads/etappe15.gpx gpx/day-15.gpx
python3 tools/build.py
```

The build reads the file, derives every number from it and writes
`data/tracks/day-15.json`. It then asks for the content it cannot know —
a stage without an entry in `data/trip.json` stops the build with the
snippet to add:

```json
{ "id": "day-15", "no": 15, "from": "Isolabona", "to": "Ventimiglia", "date": "2026-09-13" }
```

Any GPX with `<trkpt>` and `<ele>` works: komoot exports, Strava exports,
a merged file. Several `<trkseg>` are concatenated, because a stage is one
ride even when the recording was split. `<wpt>` entries become the
waypoint markers on the map.

Distance and climbing are measured on the **full-resolution** track, then
the geometry is thinned for the browser (12 m minimum spacing, 1200 points
max), so thinning does not shave kilometres off the headline numbers.
Elevation is smoothed over 5 points by default, which keeps GPS noise from
inventing a few hundred metres of ascent; `--smoothing 0` turns that off.

### Writing a summary

In `data/trip.json`, on the stage:

```json
"summary": [
  "Erster Absatz.",
  "Zweiter Absatz."
]
```

An empty list means the section shows a quiet note that the text is still
missing.

### Adding lodging

```json
"lodging": {
  "name": "Camping Le Reclard", "type": "Camping", "place": "Séez",
  "url": null, "lat": 45.62, "lon": 6.80,
  "priceEur": 14, "rating": 4, "eleM": 1050,
  "note": "Heiße Duschen, Bäcker 300 m bergab."
}
```

`lat`/`lon` are optional — with them, a flag appears on the map. Every
other field may be missing or `null`.

### Adding photos

```sh
python3 tools/prepare_photos.py day-07 ~/Pictures/RGA/day07/*.jpg
```

Resizes to 1600 px, builds 400 px thumbnails, straightens rotated phone
shots and writes the file list into `data/trip.json`. Captions are added by
hand (`"caption"`) and serve as `alt` text in the grid and as the caption in
the lightbox. Needs Pillow: `pip install Pillow`. More in `photos/README.md`.

### Renaming waypoints

Waypoints come out of komoot in English (`Shaded Cycle Path`) and live in
the generated track files, so the translations sit in `data/waypoints.json`:

```json
"names": { "Shaded Cycle Path": "Schattiger Radweg" }
```

Names without an entry show unchanged, so proper nouns like `Col de Vars`
need none. The table survives every rebuild and is read at runtime, so no
rebuild is required after editing it.

## Uploading (Hetzner web hosting)

Every path is relative, so the site also runs from a subdirectory. Upload
only:

```
index.html  stages.html  packing-list.html  day-*.html
assets/  data/  photos/  .htaccess
```

`tools/`, `templates/`, `docs/`, `gpx/` and `reference/` stay local.

```sh
export RGA_HOST=…  RGA_USER=…  RGA_PATH=/public_html
./tools/upload.sh --dry-run   # look first
./tools/upload.sh
```

The script runs `--check` first so a stale page cannot go up. Uploading
with an SFTP client works just as well: same file list, target is the
document root. `.htaccess` is optional and only sets cache times and
compression.

After uploading, open a stage page directly (`…/day-07.html`) — that shows
straight away whether `assets/` and `data/tracks/` made it.

## Layout

```
assets/css/base.css        colour tokens (tricolore on white), typography, header/footer
assets/css/site.css        landing page, stage overview, packing list
assets/css/day.css         stage page: map, profile, photo grid, lightbox
assets/js/format.js        German number and date formats
assets/js/map.js           Leaflet setup, lines, markers
assets/js/profile.js       elevation profile as SVG, cursor tied to the map
assets/js/lightbox.js      photo viewer (arrow keys, Escape, swipe)
assets/js/day.js           stage page: load the track, draw map and profile
assets/js/home.js          overview map on the landing page
assets/js/packing-list.js  packing checkboxes (localStorage)
assets/vendor/leaflet/     Leaflet 1.9.4, local instead of a CDN
tools/build.py             gpx/ + data/ → every HTML and JSON output
tools/gpx.py               GPX parsing, stats, thinning
tools/prepare_photos.py    resize, thumbnails, manifest upkeep
tools/extract_original.py  one-off migration out of the original prototype
tools/upload.sh            rsync to the web host
templates/                 the page templates the generator fills
docs/PLAN.md               how this grew out of a single HTML file
```

JavaScript only drives the map, the elevation profile, the lightbox and the
packing checkboxes. All text, figures and image references are in the HTML,
so without JavaScript only the maps are missing.

Map tiles come from OpenTopoMap and CARTO, map data from OpenStreetMap.
Passes link to quäldich.de, rides to Strava.
