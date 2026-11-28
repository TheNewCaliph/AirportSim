"""Tests for the positive Horn-rule forward-chaining engine."""

import pytest

from aom.modules.gates.rules import Fact, ForwardChainer, HornRule, Variable


def test_single_rule_inference() -> None:
    item = Variable("item")
    engine = ForwardChainer(
        [Fact("ready", ("flight-1",))],
        [HornRule(Fact("assignable", (item,)), (Fact("ready", (item,)),))],
    )

    assert Fact("assignable", ("flight-1",)) in engine.run()


def test_rule_matches_multiple_premises_and_variable_bindings() -> None:
    first = Variable("first")
    second = Variable("second")
    engine = ForwardChainer(
        [
            Fact("arrives", ("flight-1", "tail-1")),
            Fact("departs", ("flight-2", "tail-1")),
            Fact("departs", ("flight-3", "tail-2")),
        ],
        [
            HornRule(
                Fact("turn", (first, second)),
                (Fact("arrives", (first, second)), Fact("departs", (Variable("flight"), second))),
            )
        ],
    )

    assert Fact("turn", ("flight-1", "tail-1")) in engine.run()


def test_repeated_variable_must_match_same_value() -> None:
    value = Variable("value")
    engine = ForwardChainer(
        [Fact("pair", ("same", "same")), Fact("pair", ("left", "right"))],
        [
            HornRule(
                Fact("equal_pair", (value,)),
                (Fact("pair", (value, value)),),
            )
        ],
    )

    assert Fact("equal_pair", ("same",)) in engine.run()
    assert Fact("equal_pair", ("left",)) not in engine.run()


def test_empty_string_binding_is_not_treated_as_unbound() -> None:
    value = Variable("value")
    engine = ForwardChainer(
        [
            Fact("pair", ("", "different")),
            Fact("value", ("",)),
        ],
        [
            HornRule(Fact("equal_pair", (value,)), (Fact("pair", (value, value)),)),
            HornRule(Fact("copied_value", (value,)), (Fact("value", (value,)),)),
        ],
    )

    facts = engine.run()
    assert Fact("copied_value", ("",)) in facts
    assert Fact("equal_pair", ("",)) not in facts


def test_multiple_rules_deriving_same_conclusion_add_it_once() -> None:
    item = Variable("item")
    engine = ForwardChainer(
        [Fact("source_a", ("x",)), Fact("source_b", ("x",))],
        [
            HornRule(Fact("result", (item,)), (Fact("source_a", (item,)),)),
            HornRule(Fact("result", (item,)), (Fact("source_b", (item,)),)),
        ],
    )

    assert engine.run().count(Fact("result", ("x",))) == 1


def test_chained_inference_repeats_until_fixed_point() -> None:
    item = Variable("item")
    engine = ForwardChainer(
        [Fact("seed", ("x",))],
        [
            HornRule(Fact("first", (item,)), (Fact("seed", (item,)),)),
            HornRule(Fact("second", (item,)), (Fact("first", (item,)),)),
            HornRule(Fact("second", (item,)), (Fact("second", (item,)),)),
        ],
    )

    facts = engine.run()
    assert Fact("first", ("x",)) in facts
    assert Fact("second", ("x",)) in facts
    assert facts == engine.run()
    assert len(facts) == 3


def test_duplicate_base_facts_are_removed_preserving_order() -> None:
    first = Fact("known", ("a",))
    second = Fact("known", ("b",))
    engine = ForwardChainer([first, second, first], [])

    assert engine.run() == (first, second)


def test_ground_rule_with_no_premises_adds_its_conclusion() -> None:
    engine = ForwardChainer([], [HornRule(Fact("always", ("true",)), ())])

    assert engine.run() == (Fact("always", ("true",)),)


def test_rule_head_variable_must_be_bound_by_a_premise() -> None:
    with pytest.raises(ValueError, match="not bound by its premises"):
        HornRule(Fact("unsafe", (Variable("unbound"),)), (Fact("source", ()),))


def test_base_facts_must_be_ground() -> None:
    with pytest.raises(ValueError, match="base facts must be ground"):
        ForwardChainer([Fact("not_ground", (Variable("x"),))], [])


def test_fact_rejects_empty_predicate_and_non_tuple_arguments() -> None:
    with pytest.raises(ValueError, match="predicate"):
        Fact("", ())
    with pytest.raises(TypeError, match="must be a tuple"):
        Fact("invalid", ["x"])  # type: ignore[arg-type]
