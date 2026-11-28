"""Gate assignment primitives."""

from aom.modules.gates.domain import TurnContext, TurnGateDomain, derive_gate_domains
from aom.modules.gates.rules import Fact, ForwardChainer, HornRule, Variable

__all__ = [
    "Fact",
    "ForwardChainer",
    "HornRule",
    "TurnContext",
    "TurnGateDomain",
    "Variable",
    "derive_gate_domains",
]
