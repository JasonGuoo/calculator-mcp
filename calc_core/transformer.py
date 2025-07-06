"""Evaluation Transformer converting parse tree to Decimal result."""
from __future__ import annotations

import math
from decimal import Decimal, getcontext
from typing import Callable, Dict

from lark import Transformer, v_args

from .errors import CalcError

# Map of allowed constants (15 significant digits)
CONSTANTS: Dict[str, Decimal] = {
    "pi": Decimal("3.14159265358979"),
    "e": Decimal("2.71828182845905"),
}

# Helper to convert float result of math funcs to Decimal with current context
_ftod = lambda x: Decimal(str(x))

# Allowed unary functions mapping to callables that return Decimal
_FUNCS: Dict[str, Callable[[Decimal], Decimal]] = {
    "sin": lambda x: _ftod(math.sin(float(x))),
    "cos": lambda x: _ftod(math.cos(float(x))),
    "tan": lambda x: _ftod(math.tan(float(x))),
    "asin": lambda x: _ftod(math.asin(float(x))) if -1 <= x <= 1 else _raise_domain("asin"),
    "acos": lambda x: _ftod(math.acos(float(x))) if -1 <= x <= 1 else _raise_domain("acos"),
    "atan": lambda x: _ftod(math.atan(float(x))),
    "sqrt": lambda x: _ftod(math.sqrt(float(x))) if x >= 0 else _raise_domain("sqrt"),
    "exp": lambda x: _ftod(math.exp(float(x))),
    "abs": lambda x: x.copy_abs(),
}

# For functions with optional base parameter (log)

def _log(x: Decimal, b: Decimal | None = None) -> Decimal:
    if x <= 0:
        _raise_domain("log")
    if b is None:
        return _ftod(math.log(float(x)))
    if b <= 0 or b == 1:
        _raise_domain("log")
    return _ftod(math.log(float(x), float(b)))


@v_args(inline=True)  # type: ignore[arg-type]
class EvalTransformer(Transformer):
    number = lambda self, token: Decimal(token)

    def add(self, a, b):
        return a + b

    def sub(self, a, b):
        return a - b

    def mul(self, a, b):
        return a * b

    def div(self, a, b):
        if b == 0:
            raise CalcError("Division by zero")
        return a / b

    def pow(self, a, b):
        try:
            return a ** b
        except OverflowError as exc:
            raise CalcError("Power overflow") from exc

    def func(self, name_token, arg):
        name = str(name_token)
        if name == "log":
            # log(arg, base?) handled separately via grammar? For now only log(x) or log(x, base)
            if isinstance(arg, list):
                # Should not happen with current grammar
                raise CalcError("Invalid log usage")
            return _log(arg)
        func = _FUNCS.get(name)
        if not func:
            raise CalcError(f"Unknown function '{name}'")
        return func(arg)

    def __default_token__(self, token):
        # For FUNC tokens representing constants
        text = str(token)
        if text in CONSTANTS:
            return CONSTANTS[text]
        return token


def _raise_domain(func_name: str):  # helper outside class
    raise CalcError(f"DomainError: {func_name}")
