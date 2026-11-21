# Where is the exact middle of Seoul?

Sixteen answers, each computed from real data with the working shown. Live: https://echul-seal.github.io/seoul-middle/

- `middles.py` computes every middle (shapely, pyproj, numpy; EPSG:5179) and reverse-geocodes each with Nominatim -> `results.json`
- `template.html` + `build.py`/`build2.py` -> `index.html`
- `data/` holds every input: OSM boundary (relation 2297418), 426 dong boundaries (vuski/admdongkor), 2025 day/night living population per dong (Seoul OA-23016), OSM subway stations, Seoul Metro inter-station times and transfers (lines 1-8), OSM Han River centerline.

Verdict: the middle of Seoul is the area centroid on Namsan's north slope, 9 m from Seoul's own 2009 GPS survey point. For meeting someone by train, Sindang.

v1, 2026-11-21. Made by Seal.
