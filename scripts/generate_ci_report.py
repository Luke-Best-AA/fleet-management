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

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    sections = {
        "Ruff Lint": ruff["status"],
        "Ruff Format": ruff_fmt["status"],
        "Bandit": bandit["status"],
        "pip-audit": pip_audit["status"],
        "Unit Tests": tests["status"],
        "E2E Tests": e2e["status"],
        "OWASP ZAP": zap["status"],
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
    ruff_link = '<a class="detail-link" href="ruff-detail.html" target="_blank">View Full Report &rarr;</a>'
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
    html += f"""
<div class="section">
  <h2>Ruff Format {_status_badge(ruff_fmt["status"])}</h2>
  <p>{_esc(ruff_fmt["message"])}</p>
</div>
"""

    # --- Bandit ---
    bandit_link = '<a class="detail-link" href="bandit-detail.html" target="_blank">View Full Report &rarr;</a>'
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
    pip_link = '<a class="detail-link" href="pip-audit-detail.html" target="_blank">View Full Report &rarr;</a>'
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
    def _test_section(title: str, data: dict) -> str:
        s = f"""
<div class="section">
  <h2>{title} {_status_badge(data["status"])}</h2>
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

    html += _test_section("Unit &amp; Integration Tests", tests)
    html += _test_section("E2E Tests (Playwright)", e2e)

    # --- ZAP ---
    zap_links = (
        '<a class="detail-link" href="zap-report.html"'
        ' target="_blank">Full HTML Report &rarr;</a> '
        '<a class="detail-link" href="zap-detail.html"'
        ' target="_blank">JSON &rarr;</a>'
    )
    html += f"""
<div class="section">
  <h2>OWASP ZAP Baseline Scan {_status_badge(zap["status"])} {zap_links}</h2>
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

    html += """
</div>
</body>
</html>"""
    return html


def _json_viewer_html(title: str, json_data) -> str:
    """Generate a standalone HTML page that displays JSON data nicely."""
    json_str = json.dumps(json_data, indent=2, default=str) if json_data else "{}"
    escaped_json = _esc(json_str)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} — CI Detail Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #1e1e1e; color: #d4d4d4; padding: 2rem; margin: 0; }}
  h1 {{ color: #fff; margin-bottom: 0.5rem; font-size: 1.4rem; }}
  .back {{ color: #58a6ff; text-decoration: none; display: inline-block; margin-bottom: 1rem; }}
  .back:hover {{ text-decoration: underline; }}
  pre {{ background: #252526; border: 1px solid #3c3c3c; border-radius: 8px;
         padding: 1.5rem; overflow-x: auto; font-size: 0.85em; line-height: 1.5;
         white-space: pre-wrap; word-break: break-word; }}
  .key {{ color: #9cdcfe; }}
  .string {{ color: #ce9178; }}
  .number {{ color: #b5cea8; }}
  .boolean {{ color: #569cd6; }}
  .null {{ color: #569cd6; }}
</style>
</head>
<body>
<a class="back" href="ci-report.html">&larr; Back to CI Report</a>
<h1>{_esc(title)}</h1>
<pre id="json">{escaped_json}</pre>
<script>
(function() {{
  const el = document.getElementById('json');
  const raw = el.textContent;
  try {{
    const obj = JSON.parse(raw);
    const highlighted = JSON.stringify(obj, null, 2)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"([^"]+)"(?=\\s*:)/g, '<span class="key">"$1"</span>')
      .replace(/:\\s*"([^"]*)"/g, ': <span class="string">"$1"</span>')
      .replace(/:\\s*(\\d+\\.?\\d*)/g, ': <span class="number">$1</span>')
      .replace(/:\\s*(true|false)/g, ': <span class="boolean">$1</span>')
      .replace(/:\\s*(null)/g, ': <span class="null">$1</span>');
    el.innerHTML = highlighted;
  }} catch(e) {{}}
}})();
</script>
</body>
</html>"""


def generate_detail_pages():
    """Generate individual HTML detail pages for each report source."""
    import shutil

    detail_dir = REPORTS_DIR

    # JSON-based detail pages
    json_reports = [
        ("ruff.json", "Ruff Lint Report", "ruff-detail.html"),
        ("bandit.json", "Bandit Security Report", "bandit-detail.html"),
        ("pip-audit.json", "pip-audit Vulnerability Report", "pip-audit-detail.html"),
        ("zap.json", "OWASP ZAP Scan Report", "zap-detail.html"),
    ]
    for filename, title, output_name in json_reports:
        data = _load_json(filename)
        if data is not None:
            page = _json_viewer_html(title, data)
            (detail_dir / output_name).write_text(page)
            print(f"  Detail page: {output_name}")

    # Copy ZAP HTML report if it exists (produced by ZAP action)
    zap_html_src = Path("report_html.html")
    if zap_html_src.exists():
        shutil.copy(zap_html_src, detail_dir / "zap-report.html")
        print("  Copied: zap-report.html")


if __name__ == "__main__":
    REPORTS_DIR.mkdir(exist_ok=True)
    report = generate_html()
    output = REPORTS_DIR / "ci-report.html"
    output.write_text(report)
    generate_detail_pages()
    print(f"Report generated: {output}")
