"""
목적:
- 적재 작업 입력/결과 인터페이스 모델을 정의한다.

설명:
- summary/page 노드 업서트 인터페이스을 명시해 Rust 적재 브릿지와 동기화한다.

디자인 패턴:
- DTO(Data Transfer Object).

참조:
- src_py/vtree_search/ingestion/ingestor.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestionSummaryNode(BaseModel):
    """summary 노드 적재 모델."""

    node_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    summary_text: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    metadata: dict[str, object] | None = Field(default=None)


class IngestionPageNode(BaseModel):
    """page 노드 적재 모델."""

    node_id: str = Field(min_length=1)
    parent_node_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content: str = Field(default="")
    image_url: str | None = Field(default=None)
    metadata: dict[str, object] | None = Field(default=None)


class IngestionDocument(BaseModel):
    """문서 단위 적재 요청 모델."""

    document_id: str = Field(min_length=1)
    summary_nodes: list[IngestionSummaryNode] = Field(default_factory=list)
    page_nodes: list[IngestionPageNode] = Field(default_factory=list)


class IngestionResult(BaseModel):
    """적재 실행 결과 모델."""

    operation: str = Field(min_length=1)
    upserted_summary_nodes: int = Field(ge=0)
    upserted_page_nodes: int = Field(ge=0)
    touched_summary_nodes: int = Field(ge=0)
