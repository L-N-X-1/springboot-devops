#!/usr/bin/env python3
import json, os, pathlib, datetime, html

R = pathlib.Path("reports")
e = html.escape

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
]
STATUS = {"Build", "Vault file encrypted", "Semgrep (SAST)", "SonarQube gate",
          "Trivy FS (deps)", "Trivy Image", "Trivy Config"}

def cls(v):
    s = str(v)
    if s.startswith(("YES", "OK", "0 findings", "0 critical, 0 high")) or "SUCCESS" in s:
        return "ok"
    if s.startswith(("not", "UNSTABLE")):
        return "muted"
    return "bad"

body = ""
for k, v in rows:
    val = f"<span class='b {cls(v)}'>{e(str(v))}</span>" if k in STATUS else e(str(v))
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