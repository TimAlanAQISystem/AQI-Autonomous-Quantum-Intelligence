# mengine.py

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List

from metrics import Metrics


class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class Hardness(Enum):
    VAPOR = auto()
    TABLET = auto()
    TOOL = auto()
    STEEL = auto()


@dataclass
class Context:
    container_id: str
    intent: str
    role: str
    risk_level: RiskLevel
    fields: Dict[str, Any]
    mass_map: Dict[str, float]


@dataclass
class FundamentalRule:
    name: str
    description: str
    check: Callable[[Context], bool]


class MEngine:
    """
    Natural law of the system: axioms and constraints.
    """

    def __init__(self) -> None:
        self.axioms: List[FundamentalRule] = []
        self.constraints: List[FundamentalRule] = []

    def add_axiom(self, rule: FundamentalRule) -> None:
        self.axioms.append(rule)

    def add_constraint(self, rule: FundamentalRule) -> None:
        self.constraints.append(rule)

    def validate_context(self, ctx: Context) -> bool:
        for rule in self.axioms + self.constraints:
            if not rule.check(ctx):
                print(f"[MENGINE] Rule failed: {rule.name}")
                Metrics.record_mengine_violation()
                return False
        return True