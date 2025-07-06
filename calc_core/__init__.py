"""Core calculation module for Calculator MCP.
Provides `calculate(expr: str) -> Decimal` as public API.
"""
from __future__ import annotations

from decimal import Decimal, getcontext, ROUND_HALF_UP

from .errors import CalcError
from .parser import PARSER
from .transformer import EvalTransformer

# Global precision: 15 significant digits
PRECISION = 15
getcontext().prec = PRECISION + 5  # extra guard digits during intermediate steps


def _quantize(value: Decimal) -> Decimal:
    """Round/normalize result to global precision."""
    # Use normalize then quantize to significant digits
    # Build quantization exponent like 1e-(PRECISION-1)
    if value.is_zero():
        return Decimal(0)
    exponent = -(PRECISION - 1 - value.adjusted())
    quant = Decimal(10) ** exponent
    return value.quantize(quant, rounding=ROUND_HALF_UP).normalize()


def calculate(expr: str) -> Decimal:
    """Parse and evaluate the mathematical expression.

    Raises
    ------
    CalcError
        On syntax or evaluation error.
    """
    try:
        tree = PARSER.parse(expr)
        raw = EvalTransformer().transform(tree)
        return _quantize(raw)
    except CalcError:
        raise
    except Exception as exc:  # pragma: no cover
        raise CalcError(str(exc)) from exc

__all__ = ["calculate", "CalcError", "PRECISION"]
