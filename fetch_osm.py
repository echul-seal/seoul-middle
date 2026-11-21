import json, requests, time
OV = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
def q(name, ql):
    for u in OV:
        try:
            r = requests.post(u, data={"data": ql}, timeout=180, headers={"User-Agent": "seal-seoul-middle/1.0"})
            if r.ok and r.text.strip().startswith("{"):
                open(f"data/{name}.json", "w").write(r.text); print(name, "ok", u, len(r.text)); return
            print(name, u, r.status_code, r.text[:200])
        except Exception as e:
            print(name, u, "ERR", e)
        time.sleep(3)
AREA = 'area(id:3602297418)->.s;'
q("stations", '[out:json][timeout:120];' + AREA + 'nwr["railway"="station"]["station"="subway"](area.s);out center tags;')
q("han", '[out:json][timeout:120];rel["waterway"="river"]["name"="한강"];out geom;')
q("han_ways", '[out:json][timeout:120];' + AREA + 'way["waterway"="river"]["name"="한강"](area.s);out geom;')
q("markers", '[out:json][timeout:120];' + AREA + '(nwr["name"~"도로원표|중심점|칭경기념비"](area.s););out center tags;')
