#!/bin/sh
set -u
OUT=/results/$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"

# Same mechanism oscap-chroot uses: file and package probes read from /host
export OSCAP_PROBE_ROOT=/host

oscap xccdf eval \
  --profile xccdf_org.ssgproject.content_profile_cis_level1_server \
  --results-arf "$OUT/arf.xml" --report "$OUT/report.html" \
  /opt/ssg/ssg-debian12-ds.xml
rc=$?
# 0 = all pass, 2 = some rules failed (expected), anything else is a real error
[ "$rc" -eq 0 ] || [ "$rc" -eq 2 ] || exit "$rc"

python3 /usr/local/bin/summarize.py "$OUT/arf.xml" > "$OUT/summary.json"
cp "$OUT/report.html" /results/latest.html
cp "$OUT/summary.json" /results/latest.json
# keep only the 7 most recent timestamped runs
ls -1dt /results/20* | tail -n +8 | xargs -r rm -rf
