"""High-precision evaluator (34-digit) for calculator-core."""
from __future__ import annotations

import math
from decimal import Decimal, getcontext
from typing import Callable, Dict

from lark import Transformer, v_args

from .errors import CalcError

# Global precision already set in __init__.py via getcontext()
CTX = getcontext()

# 40 significant digits constants
CONSTANTS: Dict[str, Decimal] = {
    "pi": Decimal("3.141592653589793238462643383279502884197"),
    "e": Decimal("2.718281828459045235360287471352662497757"),
}

# ---------- helpers ----------

def _ftod(x: float | str) -> Decimal:
    """Convert float/str to Decimal respecting current precision."""
    return Decimal(str(x))


def _raise_domain(name: str) -> None:  # noqa: D401
    raise CalcError(f"DomainError: {name}")


# ---------- high-precision trig via Taylor (sufficient for 34-digit) ----------

_TWO_PI = CONSTANTS["pi"] * 2


def _taylor_sin(x: Decimal) -> Decimal:
    x %= _TWO_PI
    term = total = x
    k = 1
    while True:
        k += 2
        term *= -x * x / (k * (k - 1))
        if abs(term) < Decimal('1e-50'):
            return total
        total += term


def _taylor_cos(x: Decimal) -> Decimal:
    x %= _TWO_PI
    term = total = Decimal(1)
    k = 0
    while True:
        k += 2
        term *= -x * x / (k * (k - 1))
        if abs(term) < Decimal('1e-50'):
            return total
        total += term


def _taylor_tan(x: Decimal) -> Decimal:
    c = _taylor_cos(x)
    if abs(c) < Decimal('1e-32'):
        _raise_domain("tan")
    return _taylor_sin(x) / c


# ---------- unary function map ----------

_FUNCS: Dict[str, Callable[[Decimal], Decimal]] = {
    "sin": _taylor_sin,
    "cos": _taylor_cos,
    "tan": _taylor_tan,
    "asin": lambda x: _ftod(math.asin(float(x))) if -1 <= x <= 1 else _raise_domain("asin"),
    "acos": lambda x: _ftod(math.acos(float(x))) if -1 <= x <= 1 else _raise_domain("acos"),
    "atan": lambda x: _ftod(math.atan(float(x))),
    "sqrt": lambda x: x.sqrt() if x >= 0 else _raise_domain("sqrt"),
    "exp": lambda x: x.exp(),
    "abs": lambda x: x.copy_abs(),
}


# ---------- log with optional base ----------

def _log(x: Decimal, base: Decimal | None = None) -> Decimal:
    if x <= 0:
        _raise_domain("log")
    ln_x = CTX.ln(x)
    if base is None:
        return ln_x
    if base <= 0 or base == 1:
        _raise_domain("log")
    return ln_x / CTX.ln(base)


# ---------- Lark transformer ----------

@v_args(inline=True)
class EvalTransformer(Transformer):
    def __init__(self, variables: dict[str, str | int | float | Decimal] | None = None):
        super().__init__()
        self._vars: dict[str, Decimal] = {}
        if variables:
            for k, v in variables.items():
                try:
                    self._vars[k] = v if isinstance(v, Decimal) else Decimal(str(v))
                except Exception as exc:
                    raise CalcError(f"Invalid variable value for '{k}': {v}") from exc
    # terminals
    number = lambda self, token: Decimal(token)

    def const(self, token):
        """Return value of constant identifier or pass through Decimal."""
        if isinstance(token, Decimal):
            # Token already converted (possible via earlier default mappings)
            return token
        text = str(token)
        if text in CONSTANTS:
            return CONSTANTS[text]
        if text in self._vars:
            return self._vars[text]
        raise CalcError(f"Unknown identifier '{text}'")

    def arg_list(self, *items):
        return list(items)

    # binary ops
    add = lambda self, a, b: a + b
    sub = lambda self, a, b: a - b
    mul = lambda self, a, b: a * b

    def div(self, a, b):
        if b == 0:
            raise CalcError("Division by zero")
        return a / b

    def pow(self, a, b):
        try:
            return a ** b
        except (OverflowError, ValueError):
            raise CalcError("Power overflow")

    # unary ops handled via sign sequence
    def signed(self, *items):
        """Apply a chain of leading +/- signs to *value*.

        Lark may supply the sign tokens as:
        1. A `Tree('sign_seq', [...])` followed by value
        2. Individual `Token('SIGN', '+/-')` repeated, followed by value
        We flatten whatever structure comes before the value and count '-' tokens.
        """
        *sign_parts, value = items

        def _flatten(parts):
            for p in parts:
                # Recurse into iterable containers or Lark Tree-like objects
                if isinstance(p, (list, tuple)):
                    yield from _flatten(p)
                elif hasattr(p, "children"):
                    yield from _flatten(p.children)
                else:
                    yield p

        sign_tokens = [str(tok) for tok in _flatten(sign_parts) if str(tok) in '+-']
        # Discard leading '+' tokens (they're no-ops)
        while sign_tokens and sign_tokens[0] == '+':
            sign_tokens.pop(0)
        minus_count = sum(1 for t in sign_tokens if t == '-')
        return value if minus_count % 2 == 0 else -value

    # function call
    def func(self, name_token, *arg_nodes):
        name = str(name_token)
        args: list[Decimal] = []
        for n in arg_nodes:
            args.extend(n if isinstance(n, list) else [n])

        if name == "log":
            if len(args) == 1:
                return _log(args[0])
            if len(args) == 2:
                return _log(args[0], args[1])
            raise CalcError("log() takes 1 or 2 arguments")

        if len(args) != 1:
            raise CalcError(f"{name}() takes exactly 1 argument")

        func = _FUNCS.get(name)
        if not func:
            raise CalcError(f"Unknown function '{name}'")
        return func(args[0])



    # catch stray constants not handled by grammar
    def __default_token__(self, token):
        t = str(token)
        return CONSTANTS[t] if t in CONSTANTS else token
