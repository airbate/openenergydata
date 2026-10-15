"""Rule DSL: human-readable YAML quality rules for energy channels.

Each rule selects channels (by role / appliance type / channel id),
applies a deterministic check, and reports findings with an explanation.
Rules proposed by the heuristic or LLM generator carry ``confirmed:
false`` and only run after a human confirms them -- the 人机协同治理
flow at the heart of oed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

SUPPORTED_CHECKS = {"bounds", "max", "min", "zero_run", "median_above"}


@dataclass
class Rule:
    id: str
    description: str
    check: dict
    severity: str = "warning"
    origin: str = "human"           # heuristic | llm | human
    confirmed: bool = False
    reviewed_by: str | None = None
    selector: dict | None = None

    def matches(self, channel: dict) -> bool:
        sel = self.selector or {}
        if sel.get("role") and channel.get("role") != sel["role"]:
            return False
        if sel.get("channel_id") and channel.get("id") != sel["channel_id"]:
            return False
        appliance = channel.get("appliance") or {}
        if sel.get("appliance_type") and appliance.get("type") != sel["appliance_type"]:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id, "description": self.description,
            "selector": self.selector, "check": self.check,
            "severity": self.severity, "origin": self.origin,
            "confirmed": self.confirmed, "reviewed_by": self.reviewed_by,
        }

    @staticmethod
    def from_dict(d: dict) -> "Rule":
        check = d["check"]
        if check.get("type") not in SUPPORTED_CHECKS:
            raise ValueError(f"rule {d.get('id')}: unsupported check {check.get('type')}")
        return Rule(
            id=d["id"], description=d.get("description", ""),
            check=check, severity=d.get("severity", "warning"),
            origin=d.get("origin", "human"), confirmed=bool(d.get("confirmed", False)),
            reviewed_by=d.get("reviewed_by"), selector=d.get("selector"),
        )


def load_rules(path: Path) -> list[Rule]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [Rule.from_dict(r) for r in doc.get("rules", [])]


def save_rules(rules: list[Rule], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(
        {"rules": [r.to_dict() for r in rules]},
        allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text("# oed 质量规则（generated）\n" + body, encoding="utf-8")
    return path
