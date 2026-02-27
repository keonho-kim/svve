"""
목적:
- 검색 LLM 필터 입력/출력 모델을 정의한다.

설명:
- LangChain 채팅 모델 응답을 검색 파이프라인에 안전하게 매핑하기 위한 DTO를 제공한다.

디자인 패턴:
- DTO(Data Transfer Object).

참조:
- src_py/vtree_search/llm/langchain_search.py
- src_py/vtree_search/search/engine.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchFilterCandidate(BaseModel):
    """검색 LLM 필터 입력 후보 모델."""

    node_id: str = Field(min_length=1)
    content: str = Field(default="")


class SearchFilterDecision(BaseModel):
    """검색 LLM 필터 판정 모델."""

    node_id: str = Field(min_length=1)
    keep: bool
    reason: str = Field(min_length=1)
