"""Tests for the safe arithmetic expression evaluator."""

from __future__ import annotations

import pytest

from segy_toolbox.core.expression import (
    ExpressionError,
    SafeEvaluator,
    validate_expression,
)


class TestSafeEvaluator:
    """Tests for SafeEvaluator.evaluate()."""

    def setup_method(self):
        self.variables = {
            "source_x": 500000,
            "source_y": 6000000,
            "trace_index": 42,
            "coordinate_scalar": -100,
        }
        self.evaluator = SafeEvaluator(self.variables)

    # --- Basic arithmetic ---

    def test_addition(self):
        assert self.evaluator.evaluate("source_x + 100") == 500100

    def test_subtraction(self):
        assert self.evaluator.evaluate("source_x - 500000") == 0

    def test_multiplication(self):
        assert self.evaluator.evaluate("source_x * 2") == 1000000

    def test_division(self):
        assert self.evaluator.evaluate("source_x / 100") == 5000.0

    def test_floor_division(self):
        assert self.evaluator.evaluate("source_x // 3") == 166666

    def test_modulo(self):
        assert self.evaluator.evaluate("source_x % 3") == 2

    def test_power(self):
        assert self.evaluator.evaluate("2 ** 10") == 1024

    def test_combined_expression(self):
        result = self.evaluator.evaluate("source_x * 100 + 500000")
        assert result == 50500000

    def test_parentheses(self):
        result = self.evaluator.evaluate("(source_x + 1) * 2")
        assert result == 1000002

    # --- Unary operators ---

    def test_negation(self):
        assert self.evaluator.evaluate("-source_x") == -500000

    def test_positive(self):
        assert self.evaluator.evaluate("+source_x") == 500000

    # --- Variables ---

    def test_variable_lookup(self):
        assert self.evaluator.evaluate("trace_index") == 42

    def test_unknown_variable(self):
        with pytest.raises(ExpressionError, match="Unknown variable"):
            self.evaluator.evaluate("unknown_field")

    # --- Constants ---

    def test_integer_constant(self):
        assert self.evaluator.evaluate("42") == 42

    def test_float_constant(self):
        assert self.evaluator.evaluate("3.14") == 3.14

    # --- Functions ---

    def test_abs(self):
        assert self.evaluator.evaluate("abs(coordinate_scalar)") == 100

    def test_int(self):
        assert self.evaluator.evaluate("int(3.7)") == 3

    def test_round(self):
        assert self.evaluator.evaluate("round(3.14)") == 3

    def test_min(self):
        assert self.evaluator.evaluate("min(source_x, source_y)") == 500000

    def test_max(self):
        assert self.evaluator.evaluate("max(source_x, source_y)") == 6000000

    def test_float_func(self):
        assert self.evaluator.evaluate("float(trace_index)") == 42.0

    def test_unsupported_function(self):
        with pytest.raises(ExpressionError, match="Unsupported function"):
            self.evaluator.evaluate("len(source_x)")

    # --- Error handling ---

    def test_division_by_zero(self):
        with pytest.raises(ExpressionError, match="Division by zero"):
            self.evaluator.evaluate("source_x / 0")

    def test_syntax_error(self):
        with pytest.raises(ExpressionError, match="Syntax error"):
            self.evaluator.evaluate("source_x +")

    def test_string_constant_rejected(self):
        with pytest.raises(ExpressionError, match="Unsupported constant"):
            self.evaluator.evaluate("'hello'")


class TestEvaluateCondition:
    """Tests for SafeEvaluator.evaluate_condition()."""

    def setup_method(self):
        self.variables = {
            "source_x": 500000,
            "source_y": 6000000,
            "trace_index": 42,
        }
        self.evaluator = SafeEvaluator(self.variables)

    def test_greater_than_true(self):
        assert self.evaluator.evaluate_condition("source_x > 400000") is True

    def test_greater_than_false(self):
        assert self.evaluator.evaluate_condition("source_x > 600000") is False

    def test_less_than(self):
        assert self.evaluator.evaluate_condition("trace_index < 100") is True

    def test_equal(self):
        assert self.evaluator.evaluate_condition("trace_index == 42") is True

    def test_not_equal(self):
        assert self.evaluator.evaluate_condition("trace_index != 0") is True

    def test_gte(self):
        assert self.evaluator.evaluate_condition("trace_index >= 42") is True

    def test_lte(self):
        assert self.evaluator.evaluate_condition("trace_index <= 42") is True

    def test_and_operator(self):
        result = self.evaluator.evaluate_condition(
            "source_x > 0 and source_y > 0"
        )
        assert result is True

    def test_or_operator(self):
        result = self.evaluator.evaluate_condition(
            "source_x > 999999 or source_y > 0"
        )
        assert result is True

    def test_chained_comparison(self):
        result = self.evaluator.evaluate_condition("0 < trace_index < 100")
        assert result is True


class TestValidateExpression:
    """Tests for the validate_expression() helper."""

    def test_valid_expression(self):
        vars_ = ["source_x", "source_y", "trace_index"]
        assert validate_expression("source_x * 100", vars_) is None

    def test_valid_condition(self):
        vars_ = ["source_x", "trace_index"]
        assert validate_expression("source_x > 0", vars_) is None

    def test_unknown_variable(self):
        vars_ = ["source_x"]
        result = validate_expression("unknown_var + 1", vars_)
        assert result is not None
        assert "Unknown variable" in result

    def test_syntax_error(self):
        result = validate_expression("source_x +", ["source_x"])
        assert result is not None
        assert "Syntax error" in result

    def test_unsupported_function(self):
        result = validate_expression("eval('code')", ["source_x"])
        assert result is not None
        assert "Unsupported function" in result

    def test_allowed_function(self):
        vars_ = ["source_x"]
        assert validate_expression("abs(source_x)", vars_) is None
