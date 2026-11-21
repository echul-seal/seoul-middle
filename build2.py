import json
t = open("template.html").read()
rep = [
("<b>Box answers drift north-west.</b> The bounding box and the smallest enclosing circle only care about the extreme tips: the far western edge of Gangseo and the north-eastern spur toward Dobongsan. A few kilometres of outline stretch pull them toward City Hall and Seoul Station.",
 "<b>Box answers drift west.</b> The bounding box and the smallest enclosing circle ignore everything except a few extreme points of the outline. Move one tip of Gangseo or Dobong and they move; the rest of the city doesn't count. That's why they land by City Hall and Seoul Station, 1.5 to 2 km from the shape answers."),
("<b>Time pulls it east, into the old downtown.</b>", "<b>Time pulls it north-east, into the old downtown.</b>"),
]
for a, b in rep:
    assert a in t, a[:40]; t = t.replace(a, b)
open("template.html", "w").write(t)
exec(open("build.py").read())
R = json.load(open("results.json")); d = R["dist_m"]["centroid"]
t = open("site/index.html").read()
a = "<b>People pull it south.</b> Weighted by where people actually are, the center slides down Namsan's southern face toward Itaewon: the dongs south of the river carry more people per square kilometre of the shape than the ones to the north."
b = f"<b>People pull it south.</b> Weight each dong by who's in it and the center slides off the shape's balance point down Namsan's southern face: {d['popmean_night']} m for residents, {d['popmean_day']} m for the daytime crowd. Population is denser south of the centroid than north of it; by day, the offices of Gangnam and Yeouido pull harder still."
assert a in t; t = t.replace(a, b)
open("site/index.html", "w").write(t); print("ok", len(t), d)
