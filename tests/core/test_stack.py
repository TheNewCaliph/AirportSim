"""Tests for the DynamicArray-backed Stack."""

import pytest

from aom.core.stack import Stack


def test_new_stack_is_empty() -> None:
    stack: Stack[int] = Stack()

    with pytest.raises(IndexError):
        stack.peek()


def test_push_one_element() -> None:
    stack: Stack[str] = Stack()

    stack.push("boarding pass")

    assert stack.peek() == "boarding pass"


def test_push_multiple_elements() -> None:
    stack: Stack[int] = Stack()

    stack.push(1)
    stack.push(2)
    stack.push(3)

    assert stack.peek() == 3


def test_pop_returns_the_most_recently_pushed_element() -> None:
    stack: Stack[str] = Stack()
    stack.push("first")
    stack.push("last")

    assert stack.pop() == "last"


def test_stack_uses_last_in_first_out_order() -> None:
    stack: Stack[int] = Stack()
    stack.push(1)
    stack.push(2)
    stack.push(3)

    assert stack.pop() == 3
    assert stack.pop() == 2
    assert stack.pop() == 1


def test_peek_does_not_remove_the_top_element() -> None:
    stack: Stack[str] = Stack()
    stack.push("top")

    assert stack.peek() == "top"
    assert stack.peek() == "top"
    assert stack.pop() == "top"


def test_repeated_pop_operations() -> None:
    stack: Stack[int] = Stack()
    stack.push(10)
    stack.push(20)

    assert stack.pop() == 20
    assert stack.pop() == 10


def test_pop_on_empty_stack_raises_index_error() -> None:
    stack: Stack[int] = Stack()

    with pytest.raises(IndexError):
        stack.pop()


def test_peek_on_empty_stack_raises_index_error() -> None:
    stack: Stack[int] = Stack()

    with pytest.raises(IndexError):
        stack.peek()


def test_stack_supports_different_types_including_none() -> None:
    stack: Stack[object] = Stack()
    stack.push(42)
    stack.push("flight")
    stack.push(None)

    assert stack.pop() is None
    assert stack.pop() == "flight"
    assert stack.pop() == 42
