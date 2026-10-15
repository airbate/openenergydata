"""Rule engine tests: heuristic generation -> confirmation -> execution."""
from __future__ import annotations

from pathlib import Path

from oed.rules.dsl import load_rules, save_rules
from oed.rules.engine import run_rules
from oed.rules.generate import generate_heuristic


def test_heuristic_generate_and_roundtrip(oed_dataset: Path, tmp_path: Path):
    rules = generate_heuristic(oed_dataset)
    assert rules, "no heuristic rules generated"
    # oven fixture -> knowledge-base bounds rule exists
    assert any(r.id == "bounds-electric-oven" for r in rules)
    # all unconfirmed by design (human-in-the-loop)
    assert all(not r.confirmed for r in rules)
    path = save_rules(rules, tmp_path / "proposed-rules.yaml")
    loaded = load_rules(path)
    assert [r.id for r in loaded] == [r.id for r in rules]


def test_rule_selector_and_execution(oed_dataset: Path):
    rules = generate_heuristic(oed_dataset)
    # confirm every rule as the reviewer would
    for r in rules:
        r.confirmed, r.reviewed_by = True, "测试审核员"
    findings = run_rules(oed_dataset, rules)
    types = {f["type"] for f in findings}
    # fixture injected 45000 W oven sample -> bounds-electric-oven hits
    assert "rule:bounds-electric-oven" in types
    # fixture injected -35 W sample -> sanity min rule hits on ch03
    assert any(t.startswith("rule:sanity-house_1-ch03") for t in types)
    hit = next(f for f in findings if f["type"] == "rule:bounds-electric-oven")
    assert "测试审核员" in hit["detail"] and "heuristic" in hit["detail"]


def test_unconfirmed_rules_are_isolated(oed_dataset: Path):
    """The confirm flow is what promotes rules; dsl keeps both states honest."""
    rules = generate_heuristic(oed_dataset)
    assert run_rules(oed_dataset, [r for r in rules if r.confirmed]) == []
