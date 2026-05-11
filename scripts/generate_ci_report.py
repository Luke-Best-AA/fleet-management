"""Generate a combined CI report from individual job outputs.

Reads JSON/XML artifacts produced by each CI job and compiles them
into a single HTML report at reports/ci-report.html.
"""

import json
import xml.etree.ElementTree as ET  # noqa: N817
from datetime import UTC, datetime
from pathlib import Path

REPORTS_DIR = Path("reports")


def _load_json(filename: str) -> dict | list | None:
    path = REPORTS_DIR / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _load_text(filename: str) -> str | None:
    path = REPORTS_DIR / filename
    if not path.exists():
        return None
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _parse_ruff(data: list | None) -> dict:
    if data is None:
        return {"status": "skipped", "issues": []}
    issues = []
    for item in data:
        issues.append(
            {
                "file": item.get("filename", ""),
                "line": item.get("location", {}).get("row", ""),
                "code": item.get("code", ""),
                "message": item.get("message", ""),
            }
        )
    return {
        "status": "pass" if len(issues) == 0 else "fail",
        "count": len(issues),
        "issues": issues,
    }


def _parse_ruff_format(text: str | None) -> dict:
    if text is None:
        return {"status": "skipped", "message": ""}
    if "file" in text.lower() and "would be reformatted" in text.lower():
        return {"status": "fail", "message": text}
    return {"status": "pass", "message": text or "All files formatted correctly"}


def _parse_bandit(data: dict | None) -> dict:
    if data is None:
        return {"status": "skipped", "issues": []}
    results = data.get("results", [])
    metrics = data.get("metrics", {}).get("_totals", {})
    issues = []
    for r in results:
        issues.append(
            {
                "file": r.get("filename", ""),
                "line": r.get("line_number", ""),
                "severity": r.get("issue_severity", ""),
                "confidence": r.get("issue_confidence", ""),
                "test_id": r.get("test_id", ""),
                "message": r.get("issue_text", ""),
            }
        )
    return {
        "status": "pass" if len(issues) == 0 else "fail",
        "count": len(issues),
        "loc": metrics.get("loc", 0),
        "issues": issues,
    }


def _parse_pip_audit(data: dict | list | None) -> dict:
    if data is None:
        return {"status": "skipped", "vulnerabilities": []}
    deps = data if isinstance(data, list) else data.get("dependencies", [])
    vulns = []
    for dep in deps:
        for v in dep.get("vulns", []):
            vulns.append(
                {
                    "package": dep.get("name", ""),
                    "version": dep.get("version", ""),
                    "id": v.get("id", ""),
                    "description": v.get("description", ""),
                    "fix_versions": v.get("fix_versions", []),
                }
            )
    return {
        "status": "pass" if len(vulns) == 0 else "fail",
        "scanned": len(deps),
        "count": len(vulns),
        "vulnerabilities": vulns,
    }


def _parse_pytest_xml(filename: str) -> dict:
    path = REPORTS_DIR / filename
    if not path.exists():
        return {"status": "skipped", "tests": 0, "passed": 0, "failed": 0, "errors": 0, "cases": []}
    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError:
        return {"status": "error", "tests": 0, "passed": 0, "failed": 0, "errors": 0, "cases": []}

    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return {"status": "error", "tests": 0, "passed": 0, "failed": 0, "errors": 0, "cases": []}

    tests = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))

    cases = []
    for tc in suite.iter("testcase"):
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None:
            result = "failed"
            detail = failure.get("message", "")
        elif error is not None:
            result = "error"
            detail = error.get("message", "")
        elif skipped is not None:
            result = "skipped"
            detail = skipped.get("message", "")
        else:
            result = "passed"
            detail = ""
        cases.append(
            {
                "name": tc.get("name", ""),
                "classname": tc.get("classname", ""),
                "time": tc.get("time", ""),
                "result": result,
                "detail": detail,
            }
        )

    return {
        "status": "pass" if failures == 0 and errors == 0 else "fail",
        "tests": tests,
        "passed": tests - failures - errors,
        "failed": failures,
        "errors": errors,
        "time": suite.get("time", ""),
        "cases": cases,
    }


def _parse_zap(data: dict | None) -> dict:
    if data is None:
        return {"status": "skipped", "alerts": [], "count": 0, "high_risk": 0}
    sites = data.get("site", [])
    if isinstance(sites, dict):
        sites = [sites]
    alerts = []
    for site in sites:
        for alert in site.get("alerts", []):
            alerts.append(
                {
                    "name": alert.get("name", ""),
                    "risk": alert.get("riskdesc", ""),
                    "confidence": alert.get("confidence", ""),
                    "description": alert.get("desc", ""),
                    "count": alert.get("count", ""),
                }
            )
    high_risks = sum(1 for a in alerts if a.get("risk", "").lower().startswith("high"))
    return {
        "status": "pass" if high_risks == 0 else "fail",
        "count": len(alerts),
        "high_risk": high_risks,
        "alerts": alerts,
    }


def _parse_lighthouse(data: dict | None) -> dict:
    if data is None:
        return {"status": "skipped", "scores": {}, "audits": []}
    categories = data.get("categories", {})
    scores = {}
    for key, cat in categories.items():
        scores[cat.get("title", key)] = round((cat.get("score", 0) or 0) * 100)

    # Gather failed audits
    audits_data = data.get("audits", {})
    failed_audits = []
    for audit_id, audit in audits_data.items():
        score = audit.get("score")
        if score is not None and score < 1 and audit.get("scoreDisplayMode") != "informative":
            failed_audits.append(
                {
                    "id": audit_id,
                    "title": audit.get("title", ""),
                    "score": round((score or 0) * 100),
                    "description": audit.get("description", "")[:200],
                }
            )
    failed_audits.sort(key=lambda a: a["score"])

    all_pass = all(s >= 90 for s in scores.values()) if scores else False
    return {
        "status": "pass" if all_pass else ("fail" if scores else "skipped"),
        "scores": scores,
        "audits": failed_audits[:20],
    }


def _status_badge(status: str) -> str:
    colours = {
        "pass": "#28a745",
        "fail": "#dc3545",
        "skipped": "#6c757d",
        "error": "#fd7e14",
    }
    colour = colours.get(status, "#6c757d")
    label = status.upper()
    style = f"background:{colour};color:#fff;padding:2px 10px;border-radius:4px;font-size:0.85em;font-weight:600;"
    return f'<span style="{style}">{label}</span>'


def _esc(text: str) -> str:
    """Escape HTML entities."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_html() -> str:
    ruff = _parse_ruff(_load_json("ruff.json"))
    ruff_fmt = _parse_ruff_format(_load_text("ruff-format.txt"))
    bandit = _parse_bandit(_load_json("bandit.json"))
    pip_audit = _parse_pip_audit(_load_json("pip-audit.json"))
    tests = _parse_pytest_xml("pytest.xml")
    e2e = _parse_pytest_xml("e2e.xml")
    zap = _parse_zap(_load_json("zap.json"))
    lighthouse = _parse_lighthouse(_load_json("lighthouse.json"))

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    sections = {
        "Ruff Lint": ruff["status"],
        "Ruff Format": ruff_fmt["status"],
        "Bandit": bandit["status"],
        "pip-audit": pip_audit["status"],
        "Unit Tests": tests["status"],
        "E2E Tests": e2e["status"],
        "OWASP ZAP": zap["status"],
        "Lighthouse": lighthouse["status"],
    }
    overall = "pass" if all(s == "pass" for s in sections.values()) else "fail"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CI Report — Fleet Management</title>
<style>
  :root {{ --bg: #f8f9fa; --card: #fff; --border: #dee2e6; --text: #212529; --muted: #6c757d; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .timestamp {{ color: var(--muted); margin-bottom: 1.5rem; font-size: 0.9em; }}
  .summary {{ display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 2rem; }}
  .summary-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
                   padding: 0.75rem 1.25rem; flex: 1; min-width: 120px; text-align: center; }}
  .summary-card .label {{ font-size: 0.8em; color: var(--muted); text-transform: uppercase; }}
  .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
             padding: 1.5rem; margin-bottom: 1.5rem; }}
  .section h2 {{ font-size: 1.15rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th, td {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }}
  th {{ background: var(--bg); font-weight: 600; }}
  .pass-row {{ }}
  .fail-row {{ background: #fff5f5; }}
  .detail {{ color: var(--muted); font-size: 0.85em; }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .detail-link {{ font-size: 0.8em; margin-left: auto; color: #0969da; text-decoration: none; }}
  .detail-link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
<h1>CI Pipeline Report {_status_badge(overall)}</h1>
<p class="timestamp">Generated {now}</p>

<div class="summary">"""

    for name, status in sections.items():
        html += f"""
  <div class="summary-card">
    <div class="label">{_esc(name)}</div>
    <div>{_status_badge(status)}</div>
  </div>"""

    html += """
</div>
"""

    # --- Ruff Lint ---
    ruff_link = '<a class="detail-link" href="ruff-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>Ruff Lint {_status_badge(ruff["status"])} {ruff_link}</h2>"""
    if ruff["issues"]:
        html += f"""
  <p>{ruff["count"]} issue(s) found</p>
  <table>
    <tr><th>File</th><th>Line</th><th>Code</th><th>Message</th></tr>"""
        for i in ruff["issues"]:
            row = (
                '<tr class="fail-row">'
                f"<td>{_esc(i['file'])}</td>"
                f"<td>{i['line']}</td>"
                f"<td>{_esc(i['code'])}</td>"
                f"<td>{_esc(i['message'])}</td></tr>"
            )
            html += f"\n    {row}"
        html += "\n  </table>"
    else:
        html += '\n  <p class="empty">No lint issues found.</p>'
    html += "\n</div>\n"

    # --- Ruff Format ---
    ruff_fmt_link = '<a class="detail-link" href="ruff-format-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>Ruff Format {_status_badge(ruff_fmt["status"])} {ruff_fmt_link}</h2>
  <p>{_esc(ruff_fmt["message"])}</p>
</div>
"""

    # --- Bandit ---
    bandit_link = '<a class="detail-link" href="bandit-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>Bandit Security Scan {_status_badge(bandit["status"])} {bandit_link}</h2>
  <p>Scanned {bandit.get("loc", "?")} lines of code</p>"""
    if bandit["issues"]:
        html += f"""
  <p>{bandit["count"]} issue(s) found</p>
  <table>
    <tr><th>File</th><th>Line</th><th>Severity</th><th>ID</th><th>Message</th></tr>"""
        for i in bandit["issues"]:
            row = (
                '<tr class="fail-row">'
                f"<td>{_esc(i['file'])}</td>"
                f"<td>{i['line']}</td>"
                f"<td>{_esc(i['severity'])}</td>"
                f"<td>{_esc(i['test_id'])}</td>"
                f"<td>{_esc(i['message'])}</td></tr>"
            )
            html += f"\n    {row}"
        html += "\n  </table>"
    else:
        html += '\n  <p class="empty">No security issues found.</p>'
    html += "\n</div>\n"

    # --- pip-audit ---
    pip_link = '<a class="detail-link" href="pip-audit-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>pip-audit Dependency Scan {_status_badge(pip_audit["status"])} {pip_link}</h2>
  <p>Scanned {pip_audit.get("scanned", "?")} packages</p>"""
    if pip_audit["vulnerabilities"]:
        html += f"""
  <p>{pip_audit["count"]} vulnerability/ies found</p>
  <table>
    <tr><th>Package</th><th>Version</th><th>Vulnerability</th><th>Fix</th></tr>"""
        for v in pip_audit["vulnerabilities"]:
            fix = ", ".join(v["fix_versions"]) if v["fix_versions"] else "—"
            row = (
                '<tr class="fail-row">'
                f"<td>{_esc(v['package'])}</td>"
                f"<td>{_esc(v['version'])}</td>"
                f"<td>{_esc(v['id'])}</td>"
                f"<td>{_esc(fix)}</td></tr>"
            )
            html += f"\n    {row}"
        html += "\n  </table>"
    else:
        html += '\n  <p class="empty">No known vulnerabilities found.</p>'
    html += "\n</div>\n"

    # --- Test results helper ---
    def _test_section(title: str, data: dict, detail_link: str = "") -> str:
        s = f"""
<div class="section">
  <h2>{title} {_status_badge(data["status"])} {detail_link}</h2>
  <p>{data["tests"]} tests — {data["passed"]} passed, {data["failed"]} failed, {data["errors"]} errors"""
        if data.get("time"):
            s += f" ({data['time']}s)"
        s += "</p>"

        failed_cases = [c for c in data["cases"] if c["result"] in ("failed", "error")]
        if failed_cases:
            s += """
  <table>
    <tr><th>Test</th><th>Result</th><th>Detail</th></tr>"""
            for c in failed_cases:
                badge = _status_badge("fail" if c["result"] == "failed" else "error")
                test_name = f"{_esc(c['classname'])}.{_esc(c['name'])}"
                detail = _esc(c["detail"][:200])
                row = f'<tr class="fail-row"><td>{test_name}</td><td>{badge}</td><td class="detail">{detail}</td></tr>'
                s += f"\n    {row}"
            s += "\n  </table>"
        elif data["tests"] > 0:
            s += '\n  <p class="empty">All tests passed.</p>'
        s += "\n</div>\n"
        return s

    tests_link = '<a class="detail-link" href="tests-detail.html">View Full Report &rarr;</a>'
    e2e_link = '<a class="detail-link" href="e2e-detail.html">View Full Report &rarr;</a>'
    html += _test_section("Unit &amp; Integration Tests", tests, tests_link)
    html += _test_section("E2E Tests (Playwright)", e2e, e2e_link)

    # --- ZAP ---
    zap_link = '<a class="detail-link" href="zap-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>OWASP ZAP Baseline Scan {_status_badge(zap["status"])} {zap_link}</h2>
  <p>{zap["count"]} alert(s) found ({zap.get("high_risk", 0)} high risk)</p>"""
    if zap["alerts"]:
        html += """
  <table>
    <tr><th>Alert</th><th>Risk</th><th>Instances</th></tr>"""
        for a in zap["alerts"]:
            is_high = a.get("risk", "").lower().startswith("high")
            row_class = "fail-row" if is_high else ""
            html += f"""
    <tr class="{row_class}"><td>{_esc(a["name"])}</td><td>{_esc(a["risk"])}</td><td>{a["count"]}</td></tr>"""
        html += "\n  </table>"
    else:
        html += '\n  <p class="empty">No alerts raised.</p>'
    html += "\n</div>\n"

    # --- Lighthouse ---
    lh_link = '<a class="detail-link" href="lighthouse-detail.html">View Full Report &rarr;</a>'
    html += f"""
<div class="section">
  <h2>Lighthouse Audit {_status_badge(lighthouse["status"])} {lh_link}</h2>"""
    if lighthouse["scores"]:
        html += '\n  <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:0.5rem;">'
        for category, score in lighthouse["scores"].items():
            color = "#28a745" if score >= 90 else "#fd7e14" if score >= 50 else "#dc3545"
            html += (
                f'\n  <div style="text-align:center;">'
                f'<div style="font-size:1.8rem;font-weight:700;color:{color}">{score}</div>'
                f'<div style="font-size:0.8em;color:var(--muted)">{_esc(category)}</div></div>'
            )
        html += "\n  </div>"
    else:
        html += '\n  <p class="empty">No Lighthouse data available.</p>'
    html += "\n</div>\n"

    html += """
</div>
</body>
</html>"""
    return html


def _detail_page(title: str, html_content: str, json_data) -> str:
    """Generate a detail page with HTML view and JSON toggle."""
    json_str = json.dumps(json_data, indent=2, default=str)
    escaped_json = _esc(json_str)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} — CI Detail Report</title>
<style>
  :root {{ --bg: #f8f9fa; --card: #fff; --border: #dee2e6;
           --text: #212529; --muted: #6c757d; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
          Roboto, sans-serif; background: var(--bg); color: var(--text);
          line-height: 1.6; padding: 2rem; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  .back {{ color: #0969da; text-decoration: none; }}
  .back:hover {{ text-decoration: underline; }}
  h1 {{ margin: 0.5rem 0 1rem; font-size: 1.4rem; }}
  .toggle {{ display: flex; gap: 0; margin-bottom: 1.5rem; }}
  .toggle button {{ padding: 0.4rem 1.2rem; border: 1px solid var(--border);
                    background: var(--card); cursor: pointer;
                    font-size: 0.9em; color: var(--muted); }}
  .toggle button:first-child {{ border-radius: 6px 0 0 6px; }}
  .toggle button:last-child {{ border-radius: 0 6px 6px 0;
                               border-left: none; }}
  .toggle button.active {{ background: #0969da; color: #fff;
                           border-color: #0969da; }}
  #html-view {{ }}
  #json-view {{ display: none; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th, td {{ text-align: left; padding: 0.5rem 0.75rem;
            border-bottom: 1px solid var(--border); }}
  th {{ background: var(--bg); font-weight: 600; }}
  .card {{ background: var(--card); border: 1px solid var(--border);
           border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }}
  .stat {{ font-size: 2rem; font-weight: 700; }}
  .stat-label {{ font-size: 0.8em; color: var(--muted);
                 text-transform: uppercase; }}
  .stats {{ display: flex; gap: 1rem; flex-wrap: wrap;
            margin-bottom: 1.5rem; }}
  .stats .card {{ flex: 1; min-width: 100px; text-align: center; }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .severity-high {{ color: #dc3545; font-weight: 600; }}
  .severity-medium {{ color: #fd7e14; font-weight: 600; }}
  .severity-low {{ color: #ffc107; font-weight: 600; }}
  a.rule-link {{ color: #0969da; text-decoration: none; }}
  a.rule-link:hover {{ text-decoration: underline; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; border-radius: 8px;
         padding: 1.5rem; overflow-x: auto; font-size: 0.85em;
         line-height: 1.5; white-space: pre-wrap;
         word-break: break-word; }}
  .key {{ color: #9cdcfe; }}
  .string {{ color: #ce9178; }}
  .number {{ color: #b5cea8; }}
  .bool {{ color: #569cd6; }}
</style>
</head>
<body>
<div class="container">
<a class="back" href="ci-report.html">&larr; Back to CI Report</a>
<h1>{_esc(title)}</h1>
<div class="toggle">
  <button class="active" onclick="show('html')">Report</button>
  <button onclick="show('json')">JSON</button>
</div>
<div id="html-view">
{html_content}
</div>
<div id="json-view">
<pre id="json-pre">{escaped_json}</pre>
</div>
</div>
<script>
function show(view) {{
  document.getElementById('html-view').style.display =
    view === 'html' ? 'block' : 'none';
  document.getElementById('json-view').style.display =
    view === 'json' ? 'block' : 'none';
  document.querySelectorAll('.toggle button').forEach(
    function(b) {{ b.classList.remove('active'); }});
  event.target.classList.add('active');
}}
(function() {{
  var el = document.getElementById('json-pre');
  var raw = el.textContent;
  try {{
    var obj = JSON.parse(raw);
    var h = JSON.stringify(obj, null, 2)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"([^"]+)"(?=\\s*:)/g,
        '<span class="key">"$1"</span>')
      .replace(/:\\s*"([^"]*)"/g,
        ': <span class="string">"$1"</span>')
      .replace(/:\\s*(\\d+\\.?\\d*)/g,
        ': <span class="number">$1</span>')
      .replace(/:\\s*(true|false)/g,
        ': <span class="bool">$1</span>')
      .replace(/:\\s*(null)/g,
        ': <span class="bool">$1</span>');
    el.innerHTML = h;
  }} catch(e) {{}}
}})();
</script>
</body>
</html>"""


def _render_ruff_html(data: list | None) -> str:
    """Build HTML content for ruff report."""
    if not data:
        return '<p class="empty">No lint issues found.</p>'
    html = f"""<div class="stats">
  <div class="card">
    <div class="stat">{len(data)}</div>
    <div class="stat-label">Issues</div>
  </div>
</div>
<table>
<tr><th>File</th><th>Line</th><th>Rule</th><th>Message</th></tr>"""
    for item in data:
        f = _esc(item.get("filename", ""))
        row = item.get("location", {}).get("row", "")
        code = item.get("code", "")
        url = item.get("url", "")
        msg = _esc(item.get("message", ""))
        if url:
            code_cell = f'<a class="rule-link" href="{_esc(url)}" target="_blank">{_esc(code)}</a>'
        else:
            code_cell = _esc(code)
        html += f"\n<tr><td>{f}</td><td>{row}</td><td>{code_cell}</td><td>{msg}</td></tr>"
    html += "\n</table>"
    return html


def _render_bandit_html(data: dict | None) -> str:
    """Build HTML content for bandit report."""
    if not data:
        return '<p class="empty">No data available.</p>'
    results = data.get("results", [])
    metrics = data.get("metrics", {}).get("_totals", {})
    loc = metrics.get("loc", 0)
    high = metrics.get("SEVERITY.HIGH", 0)
    medium = metrics.get("SEVERITY.MEDIUM", 0)
    low = metrics.get("SEVERITY.LOW", 0)
    nosec = metrics.get("nosec", 0)
    generated = data.get("generated_at", "")

    html = f"""<div class="stats">
  <div class="card">
    <div class="stat">{loc:,}</div>
    <div class="stat-label">Lines of Code</div>
  </div>
  <div class="card">
    <div class="stat">{len(results)}</div>
    <div class="stat-label">Issues Found</div>
  </div>
  <div class="card">
    <div class="stat severity-high">{high}</div>
    <div class="stat-label">High Severity</div>
  </div>
  <div class="card">
    <div class="stat severity-medium">{medium}</div>
    <div class="stat-label">Medium Severity</div>
  </div>
  <div class="card">
    <div class="stat severity-low">{low}</div>
    <div class="stat-label">Low Severity</div>
  </div>
</div>"""
    if generated:
        html += f'<p style="color:var(--muted);font-size:0.85em;">Scanned at {_esc(generated)}</p>'
    if nosec:
        html += f'<p style="color:var(--muted);font-size:0.85em;">{nosec} nosec suppression(s)</p>'

    if results:
        html += """
<table>
<tr><th>File</th><th>Line</th><th>Severity</th><th>Confidence</th><th>Test ID</th><th>Issue</th></tr>"""
        for r in results:
            sev = r.get("issue_severity", "")
            sev_cls = f"severity-{sev.lower()}" if sev else ""
            html += (
                f"\n<tr><td>{_esc(r.get('filename', ''))}</td>"
                f"<td>{r.get('line_number', '')}</td>"
                f'<td class="{sev_cls}">{_esc(sev)}</td>'
                f"<td>{_esc(r.get('issue_confidence', ''))}</td>"
                f"<td>{_esc(r.get('test_id', ''))}</td>"
                f"<td>{_esc(r.get('issue_text', ''))}</td></tr>"
            )
        html += "\n</table>"
    else:
        html += '\n<p class="empty">No security issues found.</p>'
    return html


def _render_pip_audit_html(data: dict | list | None) -> str:
    """Build HTML content for pip-audit report."""
    if data is None:
        return '<p class="empty">No data available.</p>'
    deps = data if isinstance(data, list) else data.get("dependencies", [])
    total_vulns = sum(len(d.get("vulns", [])) for d in deps)

    html = f"""<div class="stats">
  <div class="card">
    <div class="stat">{len(deps)}</div>
    <div class="stat-label">Packages Scanned</div>
  </div>
  <div class="card">
    <div class="stat{" severity-high" if total_vulns else ""}">{total_vulns}</div>
    <div class="stat-label">Vulnerabilities</div>
  </div>
</div>"""

    if total_vulns:
        html += """
<table>
<tr><th>Package</th><th>Version</th><th>Vulnerability</th><th>Fix Versions</th><th>Description</th></tr>"""
        for dep in deps:
            for v in dep.get("vulns", []):
                fix = ", ".join(v.get("fix_versions", [])) or "—"
                desc = _esc(v.get("description", "")[:200])
                html += (
                    f"\n<tr><td>{_esc(dep.get('name', ''))}</td>"
                    f"<td>{_esc(dep.get('version', ''))}</td>"
                    f"<td>{_esc(v.get('id', ''))}</td>"
                    f"<td>{_esc(fix)}</td>"
                    f"<td>{desc}</td></tr>"
                )
        html += "\n</table>"
    else:
        html += '\n<p class="empty">No known vulnerabilities found.</p>'
    return html


def _render_zap_html(data: dict | None) -> str:
    """Build HTML content for ZAP report."""
    if not data:
        return '<p class="empty">No data available.</p>'
    sites = data.get("site", [])
    if isinstance(sites, dict):
        sites = [sites]
    alerts = []
    for site in sites:
        for alert in site.get("alerts", []):
            alerts.append(alert)

    high = sum(1 for a in alerts if a.get("riskdesc", "").lower().startswith("high"))
    medium = sum(1 for a in alerts if a.get("riskdesc", "").lower().startswith("medium"))
    low = sum(1 for a in alerts if a.get("riskdesc", "").lower().startswith("low"))
    info = sum(1 for a in alerts if a.get("riskdesc", "").lower().startswith("info"))

    html = f"""<div class="stats">
  <div class="card">
    <div class="stat">{len(alerts)}</div>
    <div class="stat-label">Total Alerts</div>
  </div>
  <div class="card">
    <div class="stat severity-high">{high}</div>
    <div class="stat-label">High</div>
  </div>
  <div class="card">
    <div class="stat severity-medium">{medium}</div>
    <div class="stat-label">Medium</div>
  </div>
  <div class="card">
    <div class="stat severity-low">{low}</div>
    <div class="stat-label">Low</div>
  </div>
  <div class="card">
    <div class="stat">{info}</div>
    <div class="stat-label">Informational</div>
  </div>
</div>"""

    if alerts:
        html += """
<table>
<tr><th>Alert</th><th>Risk</th><th>Confidence</th><th>Instances</th><th>Description</th></tr>"""
        for a in alerts:
            risk = a.get("riskdesc", "")
            risk_word = risk.split()[0].lower() if risk else ""
            risk_cls = ""
            if risk_word == "high":
                risk_cls = "severity-high"
            elif risk_word == "medium":
                risk_cls = "severity-medium"
            elif risk_word == "low":
                risk_cls = "severity-low"
            desc = _esc(a.get("desc", "").replace("<p>", "").replace("</p>", " ")[:150])
            html += (
                f"\n<tr><td>{_esc(a.get('name', ''))}</td>"
                f'<td class="{risk_cls}">{_esc(risk)}</td>'
                f"<td>{_esc(a.get('confidence', ''))}</td>"
                f"<td>{a.get('count', '')}</td>"
                f"<td>{desc}</td></tr>"
            )
        html += "\n</table>"
    else:
        html += '\n<p class="empty">No alerts raised.</p>'

    html += (
        '\n<p style="margin-top:1rem;">'
        '<a class="rule-link" href="zap-report.html" '
        'target="_blank">View full ZAP HTML report &rarr;</a></p>'
    )
    return html


def _render_lighthouse_html(data: dict | None) -> str:
    """Build HTML content for Lighthouse report."""
    if not data:
        return '<p class="empty">No data available.</p>'
    categories = data.get("categories", {})
    audits_data = data.get("audits", {})

    # Score circles
    html = '<div class="stats">'
    for _key, cat in categories.items():
        score = round((cat.get("score", 0) or 0) * 100)
        color = "#28a745" if score >= 90 else "#fd7e14" if score >= 50 else "#dc3545"
        title = _esc(cat.get("title", _key))
        html += f"""
  <div class="card" style="text-align:center;">
    <div class="stat" style="color:{color}">{score}</div>
    <div class="stat-label">{title}</div>
  </div>"""
    html += "\n</div>"

    # Failed audits table
    failed = []
    for audit_id, audit in audits_data.items():
        score = audit.get("score")
        if score is not None and score < 1 and audit.get("scoreDisplayMode") != "informative":
            failed.append((audit_id, audit))
    failed.sort(key=lambda x: x[1].get("score") or 0)

    if failed:
        html += f"""
<h3 style="margin:1.5rem 0 0.75rem;font-size:1rem;">Opportunities &amp; Diagnostics ({len(failed)} items)</h3>
<table>
<tr><th>Audit</th><th>Score</th><th>Description</th></tr>"""
        for audit_id, audit in failed[:30]:
            s = round((audit.get("score") or 0) * 100)
            color = "#28a745" if s >= 90 else "#fd7e14" if s >= 50 else "#dc3545"
            desc = _esc(audit.get("title", ""))
            html += (
                f'\n<tr><td>{_esc(audit_id)}</td><td style="color:{color};font-weight:600">{s}</td><td>{desc}</td></tr>'
            )
        html += "\n</table>"
    else:
        html += '\n<p class="empty">All audits passed.</p>'

    return html


def _render_ruff_format_html(text: str | None) -> str:
    """Build HTML content for ruff format report."""
    if text is None:
        return '<p class="empty">No data available.</p>'
    passed = "would be reformatted" not in text.lower()
    status_label = "All files formatted correctly" if passed else "Formatting issues found"
    html = f"""<div class="stats">
  <div class="card">
    <div class="stat">{"✓" if passed else "✗"}</div>
    <div class="stat-label">{status_label}</div>
  </div>
</div>
<div class="card">
  <pre style="background:var(--bg);color:var(--text);padding:1rem;margin:0;border:none;">{_esc(text)}</pre>
</div>"""
    return html


def _render_pytest_html(data: dict, coverage: dict | None = None) -> str:
    """Build HTML content for pytest report."""
    tests = data.get("tests", 0)
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)
    errors = data.get("errors", 0)
    time_s = data.get("time", "")

    cov_pct = ""
    if coverage:
        totals = coverage.get("totals", {})
        cov_pct = totals.get("percent_covered_display", "")

    html = '<div class="stats">'
    html += f"""
  <div class="card">
    <div class="stat">{tests}</div>
    <div class="stat-label">Total Tests</div>
  </div>
  <div class="card">
    <div class="stat" style="color:#28a745">{passed}</div>
    <div class="stat-label">Passed</div>
  </div>
  <div class="card">
    <div class="stat severity-high">{failed}</div>
    <div class="stat-label">Failed</div>
  </div>
  <div class="card">
    <div class="stat severity-medium">{errors}</div>
    <div class="stat-label">Errors</div>
  </div>"""
    if time_s:
        html += f"""
  <div class="card">
    <div class="stat">{time_s}s</div>
    <div class="stat-label">Duration</div>
  </div>"""
    if cov_pct:
        html += f"""
  <div class="card">
    <div class="stat">{_esc(cov_pct)}%</div>
    <div class="stat-label">Coverage</div>
  </div>"""
    html += "\n</div>"

    # Coverage breakdown by file
    if coverage and coverage.get("files"):
        html += """
<h3 style="margin:1.5rem 0 0.75rem;font-size:1rem;">Coverage by File</h3>
<table>
<tr><th>File</th><th>Statements</th><th>Missing</th><th>Coverage</th></tr>"""
        files = coverage.get("files", {})
        for filepath, info in sorted(files.items()):
            summary = info.get("summary", {})
            stmts = summary.get("num_statements", 0)
            missing = summary.get("missing_lines", 0)
            pct = summary.get("percent_covered_display", "?")
            html += f"\n<tr><td>{_esc(filepath)}</td><td>{stmts}</td><td>{missing}</td><td>{_esc(pct)}%</td></tr>"
        html += "\n</table>"

    # Test cases list
    cases = data.get("cases", [])
    if cases:
        failed_cases = [c for c in cases if c["result"] in ("failed", "error")]
        passed_cases = [c for c in cases if c["result"] == "passed"]

        if failed_cases:
            html += """
<h3 style="margin:1.5rem 0 0.75rem;font-size:1rem;color:#dc3545;">Failed Tests</h3>
<table>
<tr><th>Test</th><th>Result</th><th>Detail</th></tr>"""
            for c in failed_cases:
                test_name = f"{_esc(c['classname'])}.{_esc(c['name'])}"
                detail = _esc(c.get("detail", "")[:200])
                html += (
                    f'\n<tr class="fail-row"><td>{test_name}</td>'
                    f"<td>{'FAILED' if c['result'] == 'failed' else 'ERROR'}</td>"
                    f'<td class="detail">{detail}</td></tr>'
                )
            html += "\n</table>"

        html += f"""
<h3 style="margin:1.5rem 0 0.75rem;font-size:1rem;color:#28a745;">Passed Tests ({len(passed_cases)})</h3>
<table>
<tr><th>Test</th><th>Class</th><th>Time</th></tr>"""
        for c in passed_cases:
            html += f"\n<tr><td>{_esc(c['name'])}</td><td>{_esc(c['classname'])}</td><td>{c.get('time', '')}s</td></tr>"
        html += "\n</table>"

    return html


def generate_detail_pages():
    """Generate individual HTML detail pages for each report source."""
    import shutil

    detail_dir = REPORTS_DIR

    # Ruff
    ruff_data = _load_json("ruff.json")
    if ruff_data is not None:
        page = _detail_page("Ruff Lint Report", _render_ruff_html(ruff_data), ruff_data)
        (detail_dir / "ruff-detail.html").write_text(page)
        print("  Detail page: ruff-detail.html")

    # Bandit
    bandit_data = _load_json("bandit.json")
    if bandit_data is not None:
        page = _detail_page(
            "Bandit Security Report",
            _render_bandit_html(bandit_data),
            bandit_data,
        )
        (detail_dir / "bandit-detail.html").write_text(page)
        print("  Detail page: bandit-detail.html")

    # pip-audit
    pip_data = _load_json("pip-audit.json")
    if pip_data is not None:
        page = _detail_page(
            "pip-audit Vulnerability Report",
            _render_pip_audit_html(pip_data),
            pip_data,
        )
        (detail_dir / "pip-audit-detail.html").write_text(page)
        print("  Detail page: pip-audit-detail.html")

    # ZAP
    zap_data = _load_json("zap.json")
    if zap_data is not None:
        page = _detail_page(
            "OWASP ZAP Scan Report",
            _render_zap_html(zap_data),
            zap_data,
        )
        (detail_dir / "zap-detail.html").write_text(page)
        print("  Detail page: zap-detail.html")

    # Copy ZAP HTML report if it exists (produced by ZAP action)
    zap_html_src = Path("report_html.html")
    if zap_html_src.exists():
        shutil.copy(zap_html_src, detail_dir / "zap-report.html")
        print("  Copied: zap-report.html")

    # Ruff Format
    ruff_fmt_text = _load_text("ruff-format.txt")
    if ruff_fmt_text is not None:
        page = _detail_page(
            "Ruff Format Report",
            _render_ruff_format_html(ruff_fmt_text),
            {"output": ruff_fmt_text},
        )
        (detail_dir / "ruff-format-detail.html").write_text(page)
        print("  Detail page: ruff-format-detail.html")

    # Unit & Integration Tests
    tests_data = _parse_pytest_xml("pytest.xml")
    if tests_data["status"] != "skipped":
        coverage_data = _load_json("coverage.json")
        page = _detail_page(
            "Unit &amp; Integration Tests",
            _render_pytest_html(tests_data, coverage_data),
            {"tests": tests_data, "coverage_summary": coverage_data.get("totals") if coverage_data else None},
        )
        (detail_dir / "tests-detail.html").write_text(page)
        print("  Detail page: tests-detail.html")

    # E2E Tests
    e2e_data = _parse_pytest_xml("e2e.xml")
    if e2e_data["status"] != "skipped":
        page = _detail_page(
            "E2E Tests (Playwright)",
            _render_pytest_html(e2e_data),
            {"tests": e2e_data},
        )
        (detail_dir / "e2e-detail.html").write_text(page)
        print("  Detail page: e2e-detail.html")

    # Lighthouse
    lh_data = _load_json("lighthouse.json")
    if lh_data is not None:
        page = _detail_page(
            "Lighthouse Audit",
            _render_lighthouse_html(lh_data),
            lh_data,
        )
        (detail_dir / "lighthouse-detail.html").write_text(page)
        print("  Detail page: lighthouse-detail.html")


if __name__ == "__main__":
    REPORTS_DIR.mkdir(exist_ok=True)
    report = generate_html()
    output = REPORTS_DIR / "ci-report.html"
    output.write_text(report)
    generate_detail_pages()
    print(f"Report generated: {output}")
