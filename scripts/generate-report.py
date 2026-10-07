#!/usr/bin/env python3
import json, os, pathlib, datetime, html

R = pathlib.Path("reports")
e = html.escape

# Display threshold only: a score below this is shown in red. It never fails the build.
OSCAP_MIN_SCORE = 85.0

def load(name):
    p = R / name
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def trivy(name):
    d = load(f"trivy-{name}.json")
    if d is None:
        return "not run"
    c = {"CRITICAL": 0, "HIGH": 0}
    for res in d.get("Results", []):
        for k in ("Vulnerabilities", "Misconfigurations"):
            for f in res.get(k) or []:
                s = f.get("Severity")
                c[s] = c.get(s, 0) + 1
    return f"{c['CRITICAL']} critical, {c['HIGH']} high"

def semgrep():
    d = load("semgrep.json")
    if d is None:
        return "not run"
    res = d.get("results", [])
    if not res:
        return "0 findings"
    sev = {}
    for r in res:
        s = r["extra"].get("severity", "?")
        sev[s] = sev.get(s, 0) + 1
    top = "; ".join(f"{r['check_id'].split('.')[-1]} ({r['path']}:{r['start']['line']})" for r in res[:5])
    return f"{len(res)} findings ({', '.join(f'{v} {k}' for k, v in sev.items())}): {top}"

def sonar():
    d = load("sonar-gate.json")
    if d is None or "projectStatus" not in d:
        return "not available"
    ps = d["projectStatus"]
    bad = [f"{c['metricKey']}={c.get('actualValue')}" for c in ps.get("conditions", []) if c.get("status") == "ERROR"]
    return ps["status"] + (f" - failed: {', '.join(bad)}" if bad else "")

def openscap():
    """Compliance score = pass / (pass + fail). Rules that do not apply or are not
    selected by the profile are left out, otherwise the score would be meaningless."""
    d = load("openscap.json")
    if d is None:
        return "not run"
    p, f = d.get("pass", 0), d.get("fail", 0)
    if p + f == 0:
        return "no applicable rules were evaluated"
    score = 100.0 * p / (p + f)
    return (f"{score:.1f}% - {p} pass, {f} fail, {d.get('notapplicable', 0)} not applicable, "
            f"{d.get('notchecked', 0)} not checked")

def pods():
    p = R / "pods.txt"
    return p.read_text() if p.exists() else "not collected (deploy did not run)"

vault = pathlib.Path("ansible/group_vars/all/vault.yml")
encrypted = vault.exists() and vault.read_text().startswith("$ANSIBLE_VAULT")

rows = [
    ("Build", f"#{os.environ.get('BUILD_NUMBER')} - {os.environ.get('BUILD_RESULT')}"),
    ("Date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
    ("Duration", os.environ.get("DURATION", "n/a").replace(" and counting", "")),
    ("Image", f"{os.environ.get('IMAGE')}:{os.environ.get('IMAGE_TAG')}"),
    ("Commit", os.environ.get("GIT_COMMIT", "n/a")[:8]),
    ("Vault file encrypted", "YES" if encrypted else "NO - FIX NOW"),
    ("Semgrep (SAST)", semgrep()),
    ("SonarQube gate", sonar()),
    ("Trivy FS (deps)", trivy("fs")),
    ("Trivy Image", trivy("image")),
    ("Trivy Config", trivy("config")),
    ("OpenSCAP (node compliance)", openscap()),
    ("OpenSCAP full report", "LINK"),
]
STATUS = {"Build", "Vault file encrypted", "Semgrep (SAST)", "SonarQube gate",
          "Trivy FS (deps)", "Trivy Image", "Trivy Config", "OpenSCAP (node compliance)"}

def cls(k, v):
    s = str(v)
    if k == "OpenSCAP (node compliance)":
        try:
            return "ok" if float(s.split("%")[0]) >= OSCAP_MIN_SCORE else "bad"
        except ValueError:
            return "muted"
    if s.startswith(("YES", "OK", "0 findings", "0 critical, 0 high")) or "SUCCESS" in s:
        return "ok"
    if s.startswith(("not", "UNSTABLE")):
        return "muted"
    return "bad"

body = ""
for k, v in rows:
    if v == "LINK":
        if (R / "openscap.html").exists():
            val = "<a href='openscap.html'>Open the OpenSCAP report</a>"
        else:
            val = "<span class='b muted'>not available</span>"
    elif k in STATUS:
        val = f"<span class='b {cls(k, v)}'>{e(str(v))}</span>"
    else:
        val = e(str(v))
    body += f"<tr><th>{e(k)}</th><td>{val}</td></tr>"

CSS = """
:root{--bg:#f4f6fa;--card:#fff;--text:#1f2937;--muted:#6b7280;--line:#e5e7eb}
@media(prefers-color-scheme:dark){:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--line:#334155}}
body{font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:32px}
.wrap{max-width:860px;margin:auto}
h2{margin:0 0 20px}h3{margin:28px 0 10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:12px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child th,tr:last-child td{border-bottom:none}
th{width:210px;color:var(--muted);font-weight:600}
a{color:#2563eb}
.b{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.9em;font-weight:600}
.ok{background:#dcfce7;color:#166534}.bad{background:#fee2e2;color:#991b1b}.muted{background:#e5e7eb;color:#4b5563}
pre{background:#0f172a;color:#e2e8f0;padding:16px;border-radius:10px;overflow-x:auto;font-size:.85em}
"""

R.mkdir(exist_ok=True)
(R / "pipeline-report.html").write_text(
    f"<!doctype html><html><head><meta charset='utf-8'><title>Pipeline report</title>"
    f"<style>{CSS}</style></head><body><div class='wrap'><h2>Pipeline report</h2>"
    f"<div class='card'><table>{body}</table></div>"
    f"<h3>Deployed pods</h3><pre>{e(pods())}</pre></div></body></html>")