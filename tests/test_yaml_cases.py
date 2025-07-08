"""Parametrized tests that load all YAML files in tests/ and verify expressions.

Run with:
    uv run -m pytest -q
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

from calc_core import calculate, CalcError

TEST_DIR = Path(__file__).parent
YAML_FILES = sorted(TEST_DIR.glob("*.yaml"))


Case = Tuple[str, str | None, bool, dict]  # (expr, expected, expect_error, vars)


def _collect_cases() -> List[pytest.Param]:
    cases: List[pytest.Param] = []
    for file in YAML_FILES:
        data = yaml.safe_load(file.read_text())
        if isinstance(data, list):  # simple list of cases
            for item in data:
                if not isinstance(item, dict) or "expr" not in item:
                    # Skip comments or malformed entries
                    continue
                expr: str = item["expr"]
                expected: str | None = item.get("result")
                expect_error = "error" in item
                vars_dict = item.get("vars", {})
                id_str = f"{file.name}:{expr}"
                cases.append(pytest.param(expr, expected, expect_error, vars_dict, id=id_str))
        elif isinstance(data, dict):
            for section, items in data.items():
                for item in items:
                    if not isinstance(item, dict) or "expr" not in item:
                        continue
                    expr: str = item["expr"]
                    expected: str | None = item.get("result")
                    expect_error = section == "errors" or "error" in item
                    vars_dict = item.get("vars", {})
                    id_str = f"{file.name}:{section}:{expr}"
                    cases.append(pytest.param(expr, expected, expect_error, vars_dict, id=id_str))
        else:
            raise ValueError(f"Unsupported YAML structure in {file}")
    return cases


@pytest.mark.parametrize("expr, expected, expect_error, vars_dict", _collect_cases())
def test_expression_cases(expr: str, expected: str | None, expect_error: bool, vars_dict: dict) -> None:
    if expect_error:
        with pytest.raises(CalcError):
            calculate(expr, **vars_dict)
    else:
        result = calculate(expr, **vars_dict)
        # Allow small tolerance due to extra precision (28 decimal places)
        expected_dec = Decimal(expected)
        try:
            quant_result = result.quantize(expected_dec)
        except Exception:
            # Fallback: if expected is 0 or scientific, use same exponent as expected
            exp_digits = expected_dec.as_tuple().exponent
            quant_result = result.quantize(Decimal((0, (1,), exp_digits)))
        assert quant_result == expected_dec, (
            f"{expr} -> {result} != {expected} (after quantize {quant_result})"
        )
