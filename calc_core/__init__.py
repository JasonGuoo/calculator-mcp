"""Core calculation module for Calculator MCP.
Provides `calculate(expr: str) -> Decimal` as public API.
"""
from __future__ import annotations

from decimal import Decimal, getcontext

from .errors import CalcError
from .parser import PARSER
from .transformer import EvalTransformer

# High precision (34 significant digits similar to IEEE 128-bit)
PRECISION = 34
getcontext().prec = PRECISION


MAX_ADJ_EXP = 999  # match test expectations (10^1000 should error)


def _quantize(value: Decimal) -> Decimal:
    """Normalize result and enforce magnitude limits.

    Raises
    ------
    CalcError
        If the exponent magnitude exceeds MAX_ADJ_EXP.
    """
    if value.is_infinite():
        raise CalcError("Overflow")
    if value != 0 and abs(value.adjusted()) > MAX_ADJ_EXP:
        raise CalcError("Overflow")
    return value.normalize()


def calculate(expr: str, /, **variables) -> Decimal:
    """Parse and evaluate the mathematical expression.

    Parameters
    ----------
    expr : str
        The mathematical expression to evaluate.
    **variables : dict[str, Decimal]
        Variables to substitute into the expression.

    Raises
    ------
    CalcError
        On syntax or evaluation error.
    """
    try:
        tree = PARSER.parse(expr)
        raw = EvalTransformer(variables=variables).transform(tree)
        return _quantize(raw)
    except CalcError:
        raise
    except Exception as exc:  # pragma: no cover
        raise CalcError(str(exc)) from exc

__all__ = ["calculate", "CalcError", "PRECISION"]
