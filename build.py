import json, re
t = open("template.html").read()
t = t.replace("I computed thirteen answers", "I worked out sixteen answers").replace("<h2>Thirteen middles</h2>", "<h2>Sixteen middles</h2>").replace("Thirteen answers to one question", "Sixteen answers to one question")
t = t.replace(' Seoul has grown roughly 30 times since.', ' Today\'s Seoul is ' + '__AREA__' + ' km².')
t = t.replace("<b>People pull it south.</b> More residents live south of the river (Gangnam, Songpa, Gwanak) than the shape alone suggests, so the population centers slide down Namsan's southern face toward Itaewon.", "<b>People pull it south.</b> Weighted by where people actually are, the center slides down Namsan's southern face toward Itaewon: the dongs south of the river carry more people per square kilometre of the shape than the ones to the north.")
t = t.replace("__AREA__", "605.9")
R = json.load(open("results.json"))
t = t.replace("__DATA__", json.dumps(R, ensure_ascii=False, separators=(",", ":"))).replace("__REPO__", "https://github.com/echul-seal/seoul-middle")
open("site/index.html", "w").write(t); print(len(t))
