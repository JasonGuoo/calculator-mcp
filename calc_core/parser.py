"""Parser setup for calculator expressions using lark-parser."""
from __future__ import annotations

from lark import Lark

# Grammar mirrors the design doc
GRAMMAR = r"""
?start: sum

?sum: product
    | sum "+" product   -> add
    | sum "-" product   -> sub

?product: power
    | product "*" power  -> mul
    | product "/" power  -> div

?power: atom
    | power "^" atom     -> pow

?atom: NUMBER            -> number
    | FUNC "(" sum ")"  -> func
    | "(" sum ")"

%import common.SIGNED_NUMBER -> NUMBER
%import common.CNAME        -> FUNC
%import common.WS_INLINE
%ignore WS_INLINE
"""

PARSER: Lark = Lark(GRAMMAR, parser="lalr", lexer="contextual", propagate_positions=True)
