"""
목적:
- 검색 작업 입력 인터페이스 모델을 정의한다.

설명:
- 검색 제출 시 필요한 질의/벡터/옵션 정보를 명시적으로 검증한다.

디자인 패턴:
- DTO(Data Transfer Object).

참조:
- src_py/vtree_search/search/engine.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchSubmission(BaseModel):
    """검색 큐 제출 모델."""

    job_id: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    query_embedding: list[float] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)
    metadata: dict[str, object] | None = Field(default=None)
