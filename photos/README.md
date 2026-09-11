# Photos

One folder per stage, named after the stage id in `data/trip.json`:

```
photos/
├── day-07/
│   ├── lac-de-roselend.jpg          long edge max 1600 px, quality 80
│   └── thumbs/
│       └── lac-de-roselend.jpg      long edge 400 px, for the grid
```

The script writes both; keep the originals outside the repository:

```sh
python3 tools/prepare_photos.py day-07 ~/Pictures/RGA/day07/*.jpg
```

It straightens rotated phone shots, turns `IMG_0421.HEIC` into a web-ready
`img-0421.jpg`, builds the thumbnails and writes the file list into
`data/trip.json`. Captions are added by hand -- they become the `alt` text in
the grid and the caption in the lightbox:

```json
"photos": [{ "file": "lac-de-roselend.jpg", "caption": "Stausee von Roselend im Gegenlicht" }]
```

Then run `python3 tools/build.py` so the stage page picks up the grid.
