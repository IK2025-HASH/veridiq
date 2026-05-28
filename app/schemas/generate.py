# Copyright © 2026 Network Logic Limited. All rights reserved.

from pydantic import BaseModel, Field
from typing import Literal

GenerationType = Literal[
    "TEST_CASES",
    "BDD_SCENARIOS",
    "NEGATIVE_TEST_CASES",
    "TEST_PLAN",
    "DEFECT_REPORT",
    "EXPLORATORY_CHARTER",
    "AC_REVIEW",
    "REGRESSION_IMPACT",
]

class GenerateRequest(BaseModel):
    generation_type: GenerationType
    input_text: str = Field(..., min_length=10, max_length=5000)
    quantity: int = Field(default=1, ge=1, le=20)

class GenerateResponse(BaseModel):
    job_id: str
    generation_type: str
    content: str
    duration_ms: int | None = None
