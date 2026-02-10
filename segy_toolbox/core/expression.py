"""Safe arithmetic expression evaluator for trace header editing.

Uses Python's ast module to parse and evaluate simple arithmetic expressions,
preventing code injection. Only permits basic math operations and known
trace header field names as variables.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

# Allowed binary operators
_BINARY_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Allowed unary operators
_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Allowed comparison operators
_COMPARE_OPS: dict[type, Any] = {
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

# Allowed boolean operators
_BOOL_OPS: dict[type, Any] = {
    ast.And: all,
    ast.Or: any,
}

# Allowed function calls
_SAFE_FUNCS: dict[str, Any] = {
    "abs": abs,
    "int": int,
    "round": round,
    "min": min,
    "max": max,
    "float": float,
}


class ExpressionError(Exception):
    """Raised when an expression cannot be evaluated safely."""


class SafeEvaluator:
    """Evaluate arithmetic expressions with trace header variables only.

    Usage::

        evaluator = SafeEvaluator({"source_x": 500000, "source_y": 6000000})
        result = evaluator.evaluate("source_x * 100")
        # result = 50000000

        is_true = evaluator.evaluate_condition("source_x > 400000")
        # is_true = True
    """

    def __init__(self, variables: dict[str, int | float]):
        self.variables = variables

    def evaluate(self, expression: str) -> int | float:
        """Evaluate an arithmetic expression and return a numeric result."""
        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as e:
            raise ExpressionError(f"Syntax error in expression: {e}") from e
        return self._eval_node(tree.body)

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a boolean condition and return True/False."""
        result = self.evaluate(condition)
        return bool(result)

    def _eval_node(self, node: ast.AST) -> Any:
        # Numeric constant
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ExpressionError(f"Unsupported constant type: {type(node.value).__name__}")

        # Variable name
        if isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            raise ExpressionError(
                f"Unknown variable: '{node.id}'. "
                f"Available: {', '.join(sorted(self.variables.keys()))}"
            )

        # Binary operation: a + b, a * b, etc.
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_fn = _BINARY_OPS.get(type(node.op))
            if op_fn is None:
                raise ExpressionError(f"Unsupported operator: {type(node.op).__name__}")
            try:
                return op_fn(left, right)
            except ZeroDivisionError:
                raise ExpressionError("Division by zero")

        # Unary operation: -a, +a
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_fn = _UNARY_OPS.get(type(node.op))
            if op_fn is None:
                raise ExpressionError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_fn(operand)

        # Comparison: a > b, a == b, etc.
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                cmp_fn = _COMPARE_OPS.get(type(op))
                if cmp_fn is None:
                    raise ExpressionError(f"Unsupported comparison: {type(op).__name__}")
                if not cmp_fn(left, right):
                    return False
                left = right
            return True

        # Boolean operation: a and b, a or b
        if isinstance(node, ast.BoolOp):
            agg = _BOOL_OPS.get(type(node.op))
            if agg is None:
                raise ExpressionError(f"Unsupported boolean operator: {type(node.op).__name__}")
            values = [self._eval_node(v) for v in node.values]
            return agg(values)

        # Function call: abs(), int(), round(), min(), max()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS:
                args = [self._eval_node(a) for a in node.args]
                return _SAFE_FUNCS[node.func.id](*args)
            func_name = getattr(node.func, "id", "<unknown>")
            raise ExpressionError(
                f"Unsupported function: '{func_name}'. "
                f"Allowed: {', '.join(_SAFE_FUNCS.keys())}"
            )

        # Parenthesized expression (handled implicitly by ast)
        raise ExpressionError(f"Unsupported expression node: {type(node).__name__}")


def validate_expression(expression: str, available_vars: list[str]) -> str | None:
    """Validate an expression without evaluating it.

    Returns None if valid, or an error message string if invalid.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        return f"Syntax error: {e}"

    # Walk all nodes and check variable names
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in available_vars and node.id not in _SAFE_FUNCS:
                return f"Unknown variable: '{node.id}'"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in _SAFE_FUNCS:
                return f"Unsupported function: '{node.func.id}'"
    return None
