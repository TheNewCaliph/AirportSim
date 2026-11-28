"""A small forward-chaining engine for positive Horn rules."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Variable:
    """A named variable used in a rule pattern."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("variable name must not be empty")


@dataclass(frozen=True, slots=True)
class Fact:
    """A predicate applied to ground values or variables in a rule pattern."""

    predicate: str
    arguments: tuple[str | Variable, ...]

    def __post_init__(self) -> None:
        if not self.predicate:
            raise ValueError("fact predicate must not be empty")
        if not isinstance(self.arguments, tuple):
            raise TypeError("fact arguments must be a tuple")
        if any(not isinstance(argument, (str, Variable)) for argument in self.arguments):
            raise TypeError("fact arguments must be strings or variables")


@dataclass(frozen=True, slots=True)
class HornRule:
    """A Horn clause with one conclusion and zero or more premises."""

    head: Fact
    body: tuple[Fact, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.head, Fact):
            raise TypeError("rule head must be a Fact")
        if not isinstance(self.body, tuple):
            raise TypeError("rule body must be a tuple")
        if any(not isinstance(premise, Fact) for premise in self.body):
            raise TypeError("rule premises must be Facts")

        body_variables: list[Variable] = []
        for premise in self.body:
            for argument in premise.arguments:
                if isinstance(argument, Variable) and argument not in body_variables:
                    body_variables.append(argument)

        for argument in self.head.arguments:
            if isinstance(argument, Variable) and argument not in body_variables:
                raise ValueError(
                    f"unsafe rule: head variable {argument.name!r} is not bound by its premises"
                )


class ForwardChainer:
    """Derive facts by repeatedly applying positive Horn rules to a fixed point."""

    def __init__(self, facts: Iterable[Fact], rules: Iterable[HornRule]) -> None:
        self._facts: list[Fact] = []
        for fact in facts:
            if not isinstance(fact, Fact):
                raise TypeError("base facts must be Facts")
            if any(isinstance(argument, Variable) for argument in fact.arguments):
                raise ValueError("base facts must be ground")
            if fact not in self._facts:
                self._facts.append(fact)

        self._rules: tuple[HornRule, ...] = tuple(rules)
        if any(not isinstance(rule, HornRule) for rule in self._rules):
            raise TypeError("rules must be HornRules")

    def run(self) -> tuple[Fact, ...]:
        """Return base and inferred ground facts in deterministic insertion order."""
        facts = list(self._facts)

        while True:
            round_facts = tuple(facts)
            derived: list[Fact] = []

            for rule in self._rules:
                for bindings in _match_body(rule.body, round_facts):
                    conclusion = _instantiate(rule.head, bindings)
                    if conclusion not in facts and conclusion not in derived:
                        derived.append(conclusion)

            if not derived:
                return tuple(facts)
            facts.extend(derived)


def _match_body(
    premises: tuple[Fact, ...], facts: tuple[Fact, ...]
) -> Iterable[list[tuple[Variable, str]]]:
    """Yield bindings that satisfy every premise in order."""

    def match_at(
        index: int, bindings: list[tuple[Variable, str]]
    ) -> Iterable[list[tuple[Variable, str]]]:
        if index == len(premises):
            yield bindings
            return

        premise = premises[index]
        for fact in facts:
            next_bindings = _match(premise, fact, bindings)
            if next_bindings is not None:
                yield from match_at(index + 1, next_bindings)

    yield from match_at(0, [])


def _match(
    pattern: Fact, fact: Fact, bindings: list[tuple[Variable, str]]
) -> list[tuple[Variable, str]] | None:
    """Match one pattern against one ground fact, extending the bindings."""
    if pattern.predicate != fact.predicate or len(pattern.arguments) != len(fact.arguments):
        return None

    extended = list(bindings)
    for pattern_value, fact_value in zip(pattern.arguments, fact.arguments, strict=True):
        if isinstance(fact_value, Variable):
            raise ValueError("facts matched by the engine must be ground")
        if isinstance(pattern_value, Variable):
            for variable, existing in extended:
                if variable == pattern_value:
                    if existing != fact_value:
                        return None
                    break
            else:
                extended.append((pattern_value, fact_value))
        elif pattern_value != fact_value:
            return None
    return extended


def _instantiate(head: Fact, bindings: list[tuple[Variable, str]]) -> Fact:
    """Replace every head variable with its premise binding."""
    arguments: list[str] = []
    for argument in head.arguments:
        if isinstance(argument, Variable):
            for variable, value in bindings:
                if variable == argument:
                    arguments.append(value)
                    break
            else:
                raise ValueError(f"unbound head variable {argument.name!r}")
        else:
            arguments.append(argument)
    return Fact(head.predicate, tuple(arguments))
