import json, csv, math, time, itertools, heapq, re
import numpy as np, requests
from shapely.geometry import shape, Point, LineString, MultiLineString, mapping
from shapely.ops import transform, polylabel, linemerge, unary_union
from shapely import minimum_bounding_circle
from pyproj import Transformer
D = "data/"
fwd = Transformer.from_crs(4326, 5179, always_xy=True).transform
inv = Transformer.from_crs(5179, 4326, always_xy=True).transform
def P(lon, lat): return Point(fwd(lon, lat))
def ll(pt):
    lon, lat = inv(pt.x, pt.y); return [round(lat, 6), round(lon, 6)]
def dms(d, m, s): return d + m/60 + s/3600
out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "middles": [], "notes": {}}
def add(key, name, pt, **kw):
    out["middles"].append(dict(key=key, name=name, latlon=ll(pt), **kw)); print(key, ll(pt))

# --- boundary (OSM relation 2297418 via Nominatim)
nom = json.load(open(D+"nominatim_seoul.json"))["features"][0]["geometry"]
seoul_ll = shape(nom); seoul = transform(fwd, seoul_ll)
out["notes"]["area_km2"] = round(seoul.area/1e6, 2)
out["notes"]["boundary_vertices"] = len(seoul.exterior.coords)
# dong layer
dong = json.load(open(D+"dong.geojson"))["features"]
dgeo = {f["properties"]["adm_cd2"][:8]: transform(fwd, shape(f["geometry"])) for f in dong}
dname = {f["properties"]["adm_cd2"][:8]: f["properties"]["adm_nm"] for f in dong}
dong_union = unary_union(list(dgeo.values()))
out["notes"]["dong_union_area_km2"] = round(dong_union.area/1e6, 2)

# 1 centroid
c = seoul.centroid; add("centroid", "Area centroid", c)
cd = dong_union.centroid
out["notes"]["centroid_dong_union"] = ll(cd); out["notes"]["centroid_two_boundaries_m"] = round(c.distance(cd), 1)
# 2 bbox center
minx, miny, maxx, maxy = seoul_ll.bounds
bb = P((minx+maxx)/2, (miny+maxy)/2); add("bbox", "Bounding-box center", bb, extra={"bounds_lonlat": [minx, miny, maxx, maxy]})
# 3 pole of inaccessibility
pole = polylabel(seoul, tolerance=1.0)
add("pole", "Pole of inaccessibility", pole, extra={"distance_to_border_m": round(seoul.exterior.distance(pole), 1)})
# 4 minimum enclosing circle center
mec = minimum_bounding_circle(seoul); mc = mec.centroid
rad = max(mc.distance(Point(p)) for p in seoul.exterior.coords)
add("mec", "Smallest enclosing circle", mc, extra={"radius_m": round(rad, 1)})

# population
rows = list(csv.DictReader(open(D+"indicators.csv", encoding="utf-8-sig")))
pts, wn, wd, miss = [], [], [], []
for r in rows:
    g = dgeo.get(r["code"])
    if g is None: miss.append(r["code"]); continue
    pts.append(g.centroid); wn.append(float(r["night_population"])); wd.append(float(r["day_population"]))
X = np.array([[p.x, p.y] for p in pts]); wn = np.array(wn); wd = np.array(wd)
out["notes"]["dongs_used"] = len(pts); out["notes"]["dongs_missing"] = miss
out["notes"]["night_pop_total"] = round(wn.sum()); out["notes"]["day_pop_total"] = round(wd.sum())
def wmean(w): m = (X*w[:, None]).sum(0)/w.sum(); return Point(*m)
def weiszfeld(w, it=5000):
    y = (X*w[:, None]).sum(0)/w.sum()
    for k in range(it):
        d = np.linalg.norm(X-y, axis=1); d = np.where(d < 1e-6, 1e-6, d)
        ny = (X*(w/d)[:, None]).sum(0)/(w/d).sum()
        if np.linalg.norm(ny-y) < 1e-4: y = ny; break
        y = ny
    return Point(*y), k, float((w*np.linalg.norm(X-y, axis=1)).sum()/w.sum())
mn = wmean(wn); add("popmean_night", "Population mean center (night)", mn)
gm, k, avg = weiszfeld(wn); add("popmedian_night", "Population geometric median (night)", gm, extra={"iterations": k, "mean_dist_km": round(avg/1000, 3), "mean_dist_from_mean_center_km": round(float((wn*np.linalg.norm(X-np.array([mn.x, mn.y]), axis=1)).sum()/wn.sum())/1000, 3)})
md = wmean(wd); add("popmean_day", "Population mean center (day)", md)
gd, k2, avg2 = weiszfeld(wd); add("popmedian_day", "Population geometric median (day)", gd, extra={"iterations": k2, "mean_dist_km": round(avg2/1000, 3)})
# coarse check of median: brute grid around
# stations
st = json.load(open(D+"stations.json"))["elements"]
sp = {}
for e in st:
    lat = e.get("lat") or e["center"]["lat"]; lon = e.get("lon") or e["center"]["lon"]
    n = e["tags"].get("name", "")
    if not seoul_ll.contains(Point(lon, lat)): continue
    sp.setdefault(n, []).append((lon, lat))
uniq = {n: (np.mean([a for a, b in v]), np.mean([b for a, b in v])) for n, v in sp.items()}
SX = np.array([fwd(*v) for v in uniq.values()])
add("stations", "Subway station centroid", Point(*SX.mean(0)), extra={"stations": len(uniq), "osm_nodes": sum(len(v) for v in sp.values())})

# subway graph
def mins(s):
    m, sec = s.split(":"); return int(m)+int(sec)/60
G = {}
def edge(a, b, w):
    G.setdefault(a, {}); G.setdefault(b, {})
    G[a][b] = min(G[a].get(b, 1e9), w); G[b][a] = min(G[b].get(a, 1e9), w)
lines = {}
for r in csv.DictReader(open(D+"sd8.csv", encoding="utf-8")):
    lines.setdefault(r["호선"], []).append(r)
DWELL = 0.5
for ln, rs in lines.items():
    prev = None
    for r in rs:
        node = (r["역명"], ln); G.setdefault(node, {})
        cum = float(r["호선별누계(km)"]); dist = float(r["역간거리(km)"]); t = mins(r["소요시간"])
        if prev is not None and dist > 0:
            if abs(float(prev["호선별누계(km)"]) + dist - cum) < 0.05: src = prev
            else:
                cands = [q for q in rs if abs(float(q["호선별누계(km)"]) - (cum - dist)) < 0.05 and q is not r]
                src = cands[0] if cands else prev
                print("branch", ln, r["역명"], "<-", src["역명"])
            edge((src["역명"], ln), node, t + DWELL)
        prev = r
# 2호선 loop closure is explicit (시청 appears at start and end)
TR = 0
for r in csv.DictReader(open(D+"tr8.csv", encoding="utf-8")):
    a = r["환승역명"]; l1 = r["호선"]; l2 = re.sub("호선", "", r["환승노선"])
    t = mins(r["환승소요시간"])
    if (a, l2) in G and (a, l1) in G: edge((a, l1), (a, l2), t); TR += 1
# also link same-named nodes not covered by transfer table with 4 min default
names = {}
for n in G: names.setdefault(n[0], []).append(n)
DEF = 0
for nm, ns in names.items():
    for a, b in itertools.combinations(ns, 2):
        if b not in G[a]: edge(a, b, 4.0); DEF += 1
def dijk(s):
    dist = {s: 0}; h = [(0, s)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]: continue
        for v, w in G[u].items():
            nd = d + w
            if nd < dist.get(v, 1e18): dist[v] = nd; heapq.heappush(h, (nd, v))
    return dist
stnames = sorted(names)
res = {}
for nm in stnames:
    best = {}
    for s in names[nm]:
        for v, d in dijk(s).items():
            best[v[0]] = min(best.get(v[0], 1e18), d)
    vals = [best[x] for x in stnames if x != nm and x in best]
    res[nm] = (sum(vals)/len(vals), max(vals), len(vals))
rank = sorted(res.items(), key=lambda x: x[1][0])
rankmax = sorted(res.items(), key=lambda x: (x[1][1], x[1][0]))
out["notes"]["graph"] = {"stations": len(stnames), "line_nodes": len(G), "transfer_edges": TR, "default_transfers": DEF, "dwell_min": DWELL,
    "top10_mean": [[n, round(v[0], 2), round(v[1], 1)] for n, v in rank[:10]],
    "bottom5_mean": [[n, round(v[0], 2), round(v[1], 1)] for n, v in rank[-5:]],
    "top5_minimax": [[n, round(v[1], 1), round(v[0], 2)] for n, v in rankmax[:5]]}
def stll(nm):
    for k in (nm, nm.replace("역", ""), nm+"역"):
        if k in uniq: return uniq[k]
    for k in uniq:
        if k.startswith(nm) or nm.startswith(k): return uniq[k]
    return None
unm = [n for n in stnames if stll(n) is None]
out["notes"]["graph"]["unmatched_coords"] = unm
for key, nm, label in [("time_mean", rank[0][0], "Time middle (lowest average ride)"), ("time_minimax", rankmax[0][0], "Time middle (shortest worst-case ride)")]:
    xy = stll(nm); add(key, label, P(*xy), extra={"station": nm, "avg_min": round(res[nm][0], 2), "max_min": round(res[nm][1], 1)})

# Han river
han = json.load(open(D+"han_ways.json"))["elements"]
segs = [LineString([(g["lon"], g["lat"]) for g in e["geometry"]]) for e in han if e["type"] == "way"]
hl = transform(fwd, linemerge(MultiLineString(segs)) if len(segs) > 1 else segs[0])
clip = hl.intersection(seoul)
if clip.geom_type == "MultiLineString":
    clip2 = linemerge(clip)
    parts = list(clip2.geoms) if clip2.geom_type == "MultiLineString" else [clip2]
else: parts = [clip]
L = sum(p.length for p in parts); half = L/2; acc = 0
for p in sorted(parts, key=lambda p: -p.length):
    pass
main = max(parts, key=lambda p: p.length)
hm = main.interpolate(main.length/2)
add("han", "Midpoint of the Han's course", hm, extra={"in_seoul_km": round(L/1000, 2), "main_piece_km": round(main.length/1000, 2), "pieces": len(parts)})
out["han_line"] = [ll(Point(c)) for c in transform(lambda x, y, z=None: (x, y), main).simplify(30).coords]

# official / historical
add("doro_wonpyo", "도로원표 (road-distance origin)", P(126.9771472, 37.5701750), extra={"source": "ko.wikipedia 도로원표 (진표, 세종로네거리)"})
add("survey2009", "2009 GPS-surveyed center", P(dms(126, 59, 30.664), dms(37, 33, 6.8904)), extra={"source": "Seoul/Jung-gu, Jan 2009 (Hankook Ilbo, Asia Economy)"})
add("marker_namsan", "서울중심점 sculpture near N Seoul Tower", P(dms(126, 59, 19.6), dms(37, 33, 6.6)), extra={"source": "Atlas News: placed ~200 m from the surveyed point, 267 m elevation"})
add("stone1896", "1896 center-stone (Insa-dong)", P(126.9854332, 37.5720865), extra={"source": "ko.wikipedia 서울의 중심점 표지석"})

# distances
K = [m["key"] for m in out["middles"]]
pt = {m["key"]: P(m["latlon"][1], m["latlon"][0]) for m in out["middles"]}
out["dist_m"] = {a: {b: round(pt[a].distance(pt[b])) for b in K} for a in K}
for m in out["middles"]:
    m["to_survey2009_m"] = out["dist_m"][m["key"]]["survey2009"]
    m["in_seoul"] = seoul.contains(pt[m["key"]])
# reverse geocode
for m in out["middles"]:
    lat, lon = m["latlon"]
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18, "accept-language": "ko,en"}, headers={"User-Agent": "seal-seoul-middle/1.0 (echul-seal)"}, timeout=30).json()
        m["here"] = r.get("display_name"); m["here_name"] = r.get("name"); m["here_type"] = r.get("type")
        r2 = requests.get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18, "accept-language": "en"}, headers={"User-Agent": "seal-seoul-middle/1.0 (echul-seal)"}, timeout=30).json()
        m["here_en"] = r2.get("display_name")
    except Exception as e: m["here"] = "reverse geocode failed: %s" % e
    time.sleep(1.2)
# boundary for the map
out["boundary"] = mapping(seoul_ll.simplify(0.0004))
json.dump(out, open("results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out["notes"], ensure_ascii=False, indent=1))
for m in out["middles"]: print(m["key"], m["latlon"], m.get("here"), m["to_survey2009_m"], m.get("extra"))
