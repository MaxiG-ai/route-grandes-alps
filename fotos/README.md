# Fotos

Pro Etappe ein Ordner, benannt wie die Etappe in `data/reise.json`:

```
fotos/
├── tag-07/
│   ├── stausee-roselend.jpg          lange Kante max 1600 px, Qualität 80
│   └── thumbs/
│       └── stausee-roselend.jpg      lange Kante 400 px, fürs Raster
```

Beides erzeugt das Skript, Originale bleiben außerhalb des Repos:

```sh
python3 tools/fotos_vorbereiten.py tag-07 ~/Bilder/RGA/tag07/*.jpg
```

Es richtet gedrehte Handyfotos auf, macht aus `IMG_0421.HEIC` ein
web-taugliches `img-0421.jpg`, baut die Thumbs und schreibt die Dateiliste
nach `data/reise.json`. Die Bildtitel kommen von Hand dazu — sie stehen als
`alt`-Text im Raster und als Bildunterschrift in der Lightbox:

```json
"fotos": [{ "datei": "stausee-roselend.jpg", "titel": "Stausee von Roselend im Gegenlicht" }]
```

Danach `python3 tools/build.py`, damit die Etappenseite das Raster bekommt.
