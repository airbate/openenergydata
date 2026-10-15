"""oed command line interface."""
from __future__ import annotations

from pathlib import Path

import typer

from oed.converters import CONVERTERS
from oed.quality.scanner import ScanConfig, scan_dataset, write_report

app = typer.Typer(
    name="oed",
    help="OpenEnergyData: 统一规格转换 / 质量评注 / 基准评测",
    no_args_is_help=True,
)


@app.command()
def convert(
    dataset: str = typer.Argument(..., help="源数据集 id，如 redd"),
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


@app.command()
def rule(
    output_dir: Path = typer.Argument(...),
    ai: bool = typer.Option(False, "--ai", help="调用大模型生成领域规则（D9-10 交付）"),
):
    """LLM 领域质量规则生成与执行（开发中，见方案 D9-10）。"""
    raise typer.Exit("oed rule 将在 D9-10 实现：LLM 生成 YAML 规则 → 执行 → 解释。")


@app.command()
def report(output_dir: Path = typer.Argument(...)):
    """渲染质量报告卡 UI（Streamlit，D10 交付）。"""
    raise typer.Exit("oed report 将在 D10 实现：Streamlit 质量报告卡。")


@app.command()
def bench(output_dir: Path = typer.Argument(...)):
    """负荷预测 / NILM 基准评测（D11-12 交付）。"""
    raise typer.Exit("oed bench 将在 D11-12 实现：预测与 NILM 排行榜。")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
