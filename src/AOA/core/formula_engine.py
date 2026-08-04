from __future__ import annotations

import ast
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

SAFE_FUNCTIONS: dict[str, Callable[..., float]] = {
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "max": max,
    "min": min,
    "round": round,
    "sqrt": math.sqrt,
}


@dataclass(frozen=True)
class SafeFormula:
    source: str
    variable_names: frozenset[str]
    _tree: ast.Expression

    def evaluate(self, variables: Mapping[str, float | int]) -> float:
        missing = self.variable_names.difference(variables)
        if missing:
            raise ValueError(f"Brak zmiennych we wzorze: {', '.join(sorted(missing))}")
        value = _evaluate_node(self._tree.body, variables)
        if not math.isfinite(value):
            raise ValueError("Wynik wzoru nie jest skonczona liczba.")
        return float(value)


def compile_formula(formula: str, allowed_variables: set[str] | frozenset[str]) -> SafeFormula:
    source = str(formula).strip()
    if not source:
        raise ValueError("Wzor nie moze byc pusty.")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Nieprawidlowa skladnia wzoru: {source}") from exc

    allowed = frozenset(allowed_variables)
    used: set[str] = set()
    _validate_node(tree.body, allowed, used)
    return SafeFormula(source=source, variable_names=frozenset(used), _tree=tree)


def _validate_node(node: ast.AST, allowed: frozenset[str], used: set[str]) -> None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return
    if isinstance(node, ast.Name):
        if node.id not in allowed:
            raise ValueError(f"Niedozwolona lub nieznana zmienna we wzorze: {node.id}")
        used.add(node.id)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        _validate_node(node.operand, allowed, used)
        return
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
    ):
        _validate_node(node.left, allowed, used)
        _validate_node(node.right, allowed, used)
        return
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in SAFE_FUNCTIONS:
            raise ValueError(f"Niedozwolona funkcja we wzorze: {node.func.id}")
        if node.keywords:
            raise ValueError("Funkcje we wzorach nie obsluguja argumentow nazwanych.")
        for argument in node.args:
            _validate_node(argument, allowed, used)
        return
    raise ValueError("Niedozwolony element wzoru. Uzyj liczb, zmiennych i prostych dzialan.")


def _evaluate_node(node: ast.AST, variables: Mapping[str, float | int]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name):
        return float(variables[node.id])
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_node(node.operand, variables)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left, variables)
        right = _evaluate_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("Dzielenie przez zero we wzorze.")
            return left / right
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise ValueError("Dzielenie modulo przez zero we wzorze.")
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(right) > 12:
                raise ValueError("Wykladnik we wzorze musi byc w zakresie -12..12.")
            return left**right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = SAFE_FUNCTIONS[node.func.id]
        return float(function(*[_evaluate_node(arg, variables) for arg in node.args]))
    raise ValueError("Nie mozna obliczyc elementu wzoru.")
