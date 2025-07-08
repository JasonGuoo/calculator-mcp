from __future__ import annotations

"""Pydantic models for REST API."""

from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator


class EvaluateRequest(BaseModel):
    """Request body for `/evaluate`."""

    expr: str = Field(..., description="Expression to evaluate")
    variables: Optional[Dict[str, Decimal]] = Field(
        default=None,
        description="Optional mapping of variable names to numeric values",
    )

    # Ensure all Decimal values created with str() for precision safety
    @validator("variables", pre=True)
    def _convert_vars(cls, v):  # noqa: N805
        if v is None:
            return None
        return {k: Decimal(str(val)) for k, val in v.items()}


class EvaluateResponse(BaseModel):
    """Successful evaluation response."""

    result: str
    precision: int
