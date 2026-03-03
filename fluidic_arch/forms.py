# forms.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List
from mengine import Hardness


class FormType(Enum):
    CLUSTER = auto()
    FLOW = auto()
    WELL = auto()
    ORBIT = auto()


@dataclass
class FormStep:
    dma_name: str
    description: str


@dataclass
class Form:
    form_id: str
    name: str
    form_type: FormType
    hardness: Hardness
    steps: List[FormStep]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_pattern(self) -> Dict[str, Any]:
        return {
            "form_id": self.form_id,
            "name": self.name,
            "form_type": self.form_type.name,
            "hardness": self.hardness.name,
            "steps": [step.__dict__ for step in self.steps],
            "metadata": self.metadata,
        }

    @staticmethod
    def from_pattern(pattern: Dict[str, Any]) -> "Form":
        steps = [FormStep(**s) for s in pattern.get("steps", [])]
        return Form(
            form_id=pattern["form_id"],
            name=pattern["name"],
            form_type=FormType[pattern["form_type"]],
            hardness=Hardness[pattern["hardness"]],
            steps=steps,
            metadata=pattern.get("metadata", {}),
        )