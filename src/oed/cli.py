"""oed command line interface."""
from __future__ import annotations

from pathlib import Path

import typer

from oed.benchmark import run_forecast, run_nilm, write_leaderboard
from oed.converters import CONVERTERS
from oed.quality.scanner import ScanConfig, scan_dataset, write_report

app = typer.Typer(
    name="oed",
    help="OpenEnergyData: 统一规格转换 / 质量评注 / 基准评测",
    no_args_is_help=True,
)
rule_app = typer.Typer(help="领域质量规则：生成 / 确认 / 执行", no_args_is_help=True)
app.add_typer(rule_app, name="rule")

RULES_DIR = "rules"
PROPOSED = "rules/proposed-rules.yaml"
CONFIRMED = "rules/confirmed-rules.yaml"


@app.command()
def convert(
    dataset: str = typer.Argument(..., help=f"源数据集 id: {', '.join(sorted(CONVERTERS))}"),
    input_dir: Path = typer.Argument(..., help="原始数据集根目录"),
    output_dir: Path = typer.Argument(..., help="统一格式输出目录"),
):
    """把源数据集转换为统一 oed 格式（Parquet + 清单）。"""
    if dataset not in CONVERTERS:
        typer.echo(f"未知数据集 '{dataset}'。可用: {', '.join(sorted(CONVERTERS))}")
        raise typer.Exit(code=2)
    manifest_path = CONVERTERS[dataset].convert(input_dir, output_dir)
    typer.echo(f"✅ 转换完成，清单: {manifest_path}")


@app.command()
def scan(
    output_dir: Path = typer.Argument(..., help="统一格式数据集目录"),
    annotate: bool = typer.Option(False, "--annotate", help="将质量标记写回 parquet"),
    zero_run_minutes: float = typer.Option(60.0, help="零功率段阈值（分钟）"),
    gap_factor: float = typer.Option(3.0, help="判定缺口的时间间隔倍数"),
):
    """确定性质量扫描，产出 quality-report.{json,md}。"""
    cfg = ScanConfig(zero_run_minutes=zero_run_minutes, gap_factor=gap_factor)
    report = scan_dataset(output_dir, cfg=cfg, annotate=annotate)
    path = write_report(report, output_dir)
    typer.echo(f"✅ 扫描完成: {report['channels_scanned']} 通道，"
               f"质量得分 {report['quality_score']}/100，报告 {path}")


# ------------------------------------------------------------------ rule

@rule_app.command("generate")
def rule_generate(
    output_dir: Path = typer.Argument(..., help="统一格式数据集目录"),
    ai: bool = typer.Option(False, "--ai", help="调用大模型生成（需 OED_LLM_* 环境变量）"),
):
    """生成候选领域规则（启发式常识库或 LLM），写入 proposed-rules.yaml。"""
    from oed.rules.generate import generate_heuristic, generate_llm
    from oed.rules.dsl import save_rules

    rules = generate_llm(output_dir) if ai else generate_heuristic(output_dir)
    path = save_rules(rules, output_dir / PROPOSED)
    typer.echo(f"✅ 生成 {len(rules)} 条候选规则（均未确认）: {path}")
    typer.echo("   人工审核后执行: oed rule confirm <目录> <规则id> --by 姓名")


@rule_app.command("confirm")
def rule_confirm(
    output_dir: Path = typer.Argument(...),
    rule_id: str = typer.Argument(..., help="规则 id"),
    by: str = typer.Option("reviewer", "--by", help="审核人署名"),
):
    """确认一条候选规则（写入 confirmed-rules.yaml，人机协同留痕）。"""
    from oed.rules.dsl import load_rules, save_rules

    prop = output_dir / PROPOSED
    if not prop.exists():
        typer.echo(f"未找到 {prop}，请先执行 oed rule generate")
        raise typer.Exit(code=2)
    candidates = load_rules(prop)
    target = next((r for r in candidates if r.id == rule_id), None)
    if target is None:
        typer.echo(f"候选中不存在规则 '{rule_id}'。可用: {', '.join(r.id for r in candidates)}")
        raise typer.Exit(code=2)
    target.confirmed, target.reviewed_by = True, by
    existing = load_rules(output_dir / CONFIRMED) if (output_dir / CONFIRMED).exists() else []
    existing = [r for r in existing if r.id != rule_id] + [target]
    save_rules(existing, output_dir / CONFIRMED)
    typer.echo(f"✅ 规则 '{rule_id}' 已由 {by} 确认，将参与后续执行")


@rule_app.command("run")
def rule_run(output_dir: Path = typer.Argument(...)):
    """执行已确认的领域规则，产出 rule-findings 与报告。"""
    from oed.rules.dsl import load_rules
    from oed.rules.engine import render_findings, run_rules

    path = output_dir / CONFIRMED
    if not path.exists():
        typer.echo("没有已确认的规则（先 generate 再 confirm）")
        raise typer.Exit(code=2)
    rules = [r for r in load_rules(path) if r.confirmed]
    findings = run_rules(output_dir, rules)
    (output_dir / "rule-findings.json").write_text(
        __import__("json").dumps(findings, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (output_dir / "rule-findings.md").write_text(render_findings(findings), encoding="utf-8")
    typer.echo(f"✅ 执行 {len(rules)} 条规则，命中 {len(findings)} 项，"
               f"报告 {output_dir / 'rule-findings.md'}")


# --------------------------------------------------------------- report

@app.command()
def report(output_dir: Path = typer.Argument(...)):
    """生成自包含 HTML 质量报告卡（合并扫描 + 规则评注）。"""
    import json

    from oed.report import render_html
    from oed.rules.engine import run_rules

    scan = scan_dataset(output_dir)
    write_report(scan, output_dir)
    rule_findings = []
    confirmed = output_dir / CONFIRMED
    if confirmed.exists():
        from oed.rules.dsl import load_rules
        rule_findings = run_rules(output_dir, [r for r in load_rules(confirmed) if r.confirmed])
        (output_dir / "rule-findings.json").write_text(
            json.dumps(rule_findings, ensure_ascii=False, indent=2), encoding="utf-8")
    path = render_html(output_dir, scan, rule_findings)
    typer.echo(f"✅ HTML 报告卡: {path}")


# ---------------------------------------------------------------- bench

@app.command()
def bench(
    output_dir: Path = typer.Argument(...),
    task: str = typer.Option("all", "--task", help="forecast | nilm | all"),
    train_frac: float = typer.Option(0.8, help="训练集时间占比"),
):
    """运行基准评测（负荷预测基线 / NILM 框架），产出排行榜。"""
    if task not in ("forecast", "nilm", "all"):
        raise typer.BadParameter("task 必须是 forecast/nilm/all")
    rows = []
    if task in ("forecast", "all"):
        rows += run_forecast(output_dir, train_frac)
    if task in ("nilm", "all"):
        rows += run_nilm(output_dir, train_frac)
    if not rows:
        typer.echo("没有可评测的通道（需要 site_meter 通道做预测 / submeter 做 NILM）")
        raise typer.Exit(code=1)
    path = write_leaderboard(rows, output_dir)
    typer.echo(f"✅ 基准完成: {len(rows)} 行结果，排行榜 {path}")


@app.command("check")
def check(
    sources: list[Path] = typer.Argument(None, help="Feather V2 原始文件，可多个"),
    dataset: Path | None = typer.Option(None, "--dataset", help="统一格式数据集目录"),
    output: Path = typer.Option(Path("trust-report"), "--output", "-o"),
    checksums: Path | None = typer.Option(None, "--checksums", help="JSON 文件名到 SHA-256 的映射（参考来源需自行确认）"),
):
    """只读检查结构、身份表示和单位声明；失败退出码 2，其余为 0。"""
    import json
    import re
    from oed.trust import check_inputs, write_check_report
    hashes = None
    if checksums:
        try:
            hashes = json.loads(checksums.read_text())
            if not isinstance(hashes, dict) or not all(isinstance(k, str) and isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v) for k, v in hashes.items()):
                raise ValueError("expected a filename-to-SHA256 object")
            hashes = {k: v.lower() for k, v in hashes.items()}
        except (OSError, ValueError) as error:
            raise typer.BadParameter(str(error), param_hint="--checksums") from error
    try:
        report = check_inputs(sources or [], dataset, hashes)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if checksums and checksums.resolve() in {(output/name).resolve() for name in ('check-report.json', 'check-report.md', 'check-report.html')}:
        raise typer.BadParameter('Report output would overwrite the checksum reference; choose another output directory')
    try:
        path = write_check_report(report, output)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"检查完成：{report['status']}，报告 {path}")
    if report['status'] == 'fail':
        raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
