"""Self-contained HTML quality report card (no server needed)."""
from __future__ import annotations

import html
from pathlib import Path

from oed.io import load_manifest

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
       margin: 0; background: #f5f7fa; color: #1f2933; }
.wrap { max-width: 960px; margin: 0 auto; padding: 32px 20px 60px; }
header { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.score { width: 120px; height: 120px; border-radius: 50%;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; font-weight: 700; }
.score b { font-size: 34px; }
.score span { font-size: 12px; opacity: .8; }
.good { background: #e3f6e8; color: #14532d; }
.warn { background: #fdf3d7; color: #713f12; }
.bad  { background: #fde3e1; color: #7f1d1d; }
h1 { font-size: 22px; margin: 0; }
.meta { color: #52606d; font-size: 13px; margin-top: 6px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 18px 0; }
.chip { background: #fff; border: 1px solid #d9e2ec; border-radius: 999px;
        padding: 4px 12px; font-size: 13px; }
.chip b { color: #102a43; }
.crit { border-color: #f0a4a0; background: #fff5f4; }
section { background: #fff; border: 1px solid #e1e8f0; border-radius: 12px;
          padding: 18px 20px; margin-top: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: #52606d; font-weight: 600;
     border-bottom: 2px solid #e1e8f0; padding: 8px 6px; }
td { border-bottom: 1px solid #f0f4f8; padding: 8px 6px; vertical-align: top; }
.badge { display: inline-block; padding: 1px 8px; border-radius: 4px;
         font-size: 12px; font-weight: 600; }
.b-critical { background: #fde3e1; color: #7f1d1d; }
.b-warning  { background: #fdf3d7; color: #713f12; }
.b-info     { background: #e3e8fd; color: #1e3a8a; }
footer { margin-top: 26px; color: #829ab1; font-size: 12px; }
"""


def render_html(dataset_dir: Path, scan_report: dict,
                rule_findings: list[dict]) -> Path:
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    name = html.escape(str(manifest.get("name", "")))
    sites = manifest.get("x-oed", {}).get("sites", [])
    n_channels = sum(len(s.get("channels", [])) for s in sites)

    score = float(scan_report.get("quality_score", 0))
    grade = "good" if score >= 80 else ("warn" if score >= 60 else "bad")

    def sev_badge(sev: str) -> str:
        return f'<span class="badge b-{html.escape(sev)}">{html.escape(sev)}</span>'

    def esc(v) -> str:
        return html.escape(str(v))

    def finding_rows(findings: list[dict], with_sev: bool = True) -> str:
        if not findings:
            return '<tr><td colspan="5" style="color:#829ab1">✅ 无发现</td></tr>'
        out = []
        for f in findings:
            sev = f"<td>{sev_badge(f['severity'])}</td>" if with_sev else ""
            out.append(
                f"<tr>{sev}<td><code>{esc(f['channel'])}</code></td>"
                f"<td>{esc(str(f['start'])[:19])}<br>{esc(str(f['end'])[:19])}</td>"
                f"<td>{esc(f['detail'])}</td></tr>")
        return "".join(out)

    summary = scan_report.get("summary", {})
    chips = "".join(
        f'<span class="chip{" crit" if k in ("impossible_value", "unit_anomaly") else ""}">'
        f'{esc(k)} <b>{v}</b></span>'
        for k, v in sorted(summary.items())) or '<span class="chip">全部通过 ✅</span>'

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · oed 质量报告</title><style>{_CSS}</style></head>
<body><div class="wrap">
<header>
  <div class="score {grade}"><b>{score:g}</b><span>/ 100 质量得分</span></div>
  <div>
    <h1>{name}</h1>
    <div class="meta">{esc(manifest.get('description', ''))}</div>
    <div class="meta">站点 {len(sites)} · 通道 {n_channels} ·
      扫描时间 {esc(scan_report.get('generated_at', '')[:19])} ·
      许可 {esc(str(manifest.get('license', '')))}</div>
    <div class="meta">清单兼容 Croissant (MLCommons) · 规格 {esc(manifest.get('x-oed', {}).get('spec', ''))}</div>
  </div>
</header>
<div class="chips">{chips}</div>
<section>
  <h3>确定性扫描发现</h3>
  <table><tr><th>级别</th><th>通道</th><th>时间范围</th><th>说明</th></tr>
  {finding_rows(scan_report.get('findings', []))}</table>
</section>
<section>
  <h3>领域规则评注（人机协同）</h3>
  <table><tr><th>级别</th><th>通道</th><th>时间范围</th><th>说明</th></tr>
  {finding_rows(rule_findings)}</table>
</section>
<footer>由 OpenEnergyData (oed) 生成 · Apache-2.0 · 证据可追溯至 quality-report.json</footer>
</div></body></html>"""
    path = dataset_dir / "quality-report.html"
    path.write_text(doc, encoding="utf-8")
    return path
