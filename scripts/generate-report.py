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
body = "".join(f"<tr><th align=left>{e(a)}</th><td>{e(str(b))}</td></tr>" for a, b in rows)
R.mkdir(exist_ok=True)
(R / "pipeline-report.html").write_text(
    "<html><body style='font-family:sans-serif'><h2>Pipeline report</h2>"
    f"<table border=1 cellpadding=6 style='border-collapse:collapse'>{body}</table>"
    f"<h3>Deployed pods</h3><pre>{e(pods())}</pre></body></html>")