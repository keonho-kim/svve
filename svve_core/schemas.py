from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: np.ndarray
    top_k: int = Field(default=10, ge=1)

    @field_validator("query", mode="before")
    @classmethod
    def validate_query(cls, value: object) -> np.ndarray:
        query = np.ascontiguousarray(np.asarray(value, dtype=np.float32))
        if query.ndim != 1:
            raise ValueError("query must be a 1D numpy array")
        return query
