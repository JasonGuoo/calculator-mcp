"""Parser setup for calculator expressions using lark-parser."""
from __future__ import annotations

from lark import Lark

# Grammar mirrors the design doc
GRAMMAR = r"""
?start: expr

?expr: sum

?sum: product
    | sum "+" product   -> add
    | sum "-" product   -> sub

?product: unary
    | product "*" power  -> mul
    | product "/" power  -> div


// Exponentiation (right-associative) binds tighter than unary
?power: atom "^" power   -> pow
      | atom

// Unary plus/minus
?unary: sign_seq power   -> signed
      | power

sign_seq: SIGN+
SIGN: "+" | "-"

?atom: NUMBER              -> number
     | FUNC "(" args ")" -> func
     | FUNC                -> const
     | "(" expr ")"

// Comma-separated argument list
?args: expr ("," expr)*   -> arg_list




// Define unsigned number token (no leading sign)
NUMBER: /[0-9]+(\.[0-9]+)?([eE][+-]?\d+)?/
%import common.CNAME        -> FUNC
%import common.WS_INLINE
%ignore WS_INLINE
"""

PARSER: Lark = Lark(GRAMMAR, parser="lalr", lexer="contextual", propagate_positions=True)
