import sys, json, collections
import xml.etree.ElementTree as ET

counts = collections.Counter()
for el in ET.parse(sys.argv[1]).iter():
    if el.tag.endswith("}rule-result"):
        res = next((c.text for c in el if c.tag.endswith("}result")), "unknown")
        counts[res] += 1
print(json.dumps({"total": sum(counts.values()), **counts}, indent=2))
