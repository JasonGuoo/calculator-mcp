from __future__ import annotations

"""Resource & function registry for the Calculator MCP server."""

from decimal import getcontext
from typing import Any, Dict, List, Optional, Tuple

from lark import Lark

from calc_core.transformer import EvalTransformer, CalcError

# --------------------------- grammar & parser ----------------------------
# Minimal Lark grammar matching EvalTransformer rule names
_CALC_GRAMMAR = r"""
    ?start: expr

    ?expr: expr "+" term   -> add
         | expr "-" term   -> sub
         | term

    ?term: term "*" power  -> mul
         | term "/" power  -> div
         | power

    ?power: factor "^" power -> pow
          | factor

    ?factor: func_call
           | constant       -> const
           | NUMBER         -> number
           | "-" factor     -> signed
           | "(" expr ")"

    func_call: NAME "(" arg_list? ")" -> func
    arg_list: expr ("," expr)*

    constant: NAME

    %import common.CNAME -> NAME
    %import common.SIGNED_NUMBER -> NUMBER
    %import common.WS_INLINE
    %ignore WS_INLINE
"""

_PARSER = Lark(_CALC_GRAMMAR, parser="lalr", transformer=None, maybe_placeholders=False)


def _evaluate_expr(expr: str, variables: dict | None = None) -> str:
    """Evaluate *expr* with high precision using EvalTransformer & Lark."""
    transformer = EvalTransformer(variables)
    tree = _PARSER.parse(expr)
    result = transformer.transform(tree)  # type: ignore[arg-type]
    return str(result)


# --------------------------- registry class -----------------------------

class ResourceRegistry:
    """In-memory registry for resources and callable functions."""

    def __init__(self) -> None:
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}

    # Resource management -------------------------------------------------
    def add_resource(self, uri: str, meta: Dict[str, Any]) -> None:
        self._resources[uri] = meta

    def list_resources(self, cursor: Optional[str] = None, limit: int = 50) -> Tuple[List[Tuple[str, Dict[str, Any]]], Optional[str]]:
        items = list(self._resources.items())
        start = int(cursor) if cursor else 0
        end = start + limit
        next_cursor = str(end) if end < len(items) else None
        return items[start:end], next_cursor

    def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        return self._resources.get(uri)

    # Function management -------------------------------------------------
    def add_function(self, name: str, meta: Dict[str, Any]) -> None:
        self._functions[name] = meta

    def list_functions(self) -> Dict[str, Dict[str, Any]]:
        return self._functions

    def get_function(self, name: str) -> Optional[Dict[str, Any]]:
        return self._functions.get(name)


registry = ResourceRegistry()


# Register default calculator function
registry.add_function(
    "calc.evaluate",
    {
        "description": "Evaluate a math expression with 34-digit precision.",
            "parameters": {
                "expr": {
                    "type": "string",
                    "description": "Mathematical expression supporting + - * / ^, parentheses, predefined constants and functions."
                },
                "variables": {
                    "type": "object",
                    "description": "Optional mapping of variable names to numeric values overriding default constants.",
                    "schema": {"additionalProperties": {"type": "number"}},
                    "optional": True
                }
            },
            "predefined_constants": {
                "pi": "3.14159265358979",
                "e": "2.71828182845905"
            },
            "supported_functions": ["sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "log", "exp", "abs"],
            "examples": [
                {"expr": "sin(pi/2)", "result": "1"},
                {"expr": "log(100,10)", "result": "2"},
                {"expr": "sqrt(16)+tan(pi/4)", "result": "5"}
            ],
            "handler": _evaluate_expr,
    },
)
