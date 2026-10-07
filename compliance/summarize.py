import sys, json, collections
from defusedxml.ElementTree import parse

counts = collections.Counter()
for el in parse(sys.argv[1]).iter():
    if el.tag.endswith("}rule-result"):
        res = next((c.text for c in el if c.tag.endswith("}result")), "unknown")
        counts[res] += 1
print(json.dumps({"total": sum(counts.values()), **counts}, indent=2))