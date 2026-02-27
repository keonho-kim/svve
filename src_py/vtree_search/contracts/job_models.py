"""
목적:
- 검색 잡 상태/결과 인터페이스 모델을 정의한다.

설명:
- 큐 상태를 문자열 상수로 통일하고 API 응답 모델로 재사용한다.

디자인 패턴:
- 상태 객체(State DTO).

참조:
- src_py/vtree_search/search/engine.py
- src_py/vtree_search/queue/redis_streams.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JobState = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"]


class SearchJobAccepted(BaseModel):
    """검색 작업 접수 응답 모델."""

    job_id: str = Field(min_length=1)
    state: JobState = Field(default="PENDING")
    submitted_at: str = Field(min_length=1)


class SearchJobStatus(BaseModel):
    """검색 작업 상태 조회 모델."""

    job_id: str = Field(min_length=1)
    state: JobState
    retries: int = Field(default=0, ge=0)
    canceled: bool = Field(default=False)
    updated_at: str = Field(min_length=1)
    last_error: str | None = Field(default=None)


class SearchCandidate(BaseModel):
    """검색 결과 후보 모델."""

    node_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    content: str = Field(default="")
    image_url: str | None = Field(default=None)
    reason: str = Field(default="")


class SearchMetrics(BaseModel):
    """검색 파이프라인 메트릭 모델."""

    entry_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    kept_count: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)


class SearchJobResult(BaseModel):
    """검색 작업 최종 결과 모델."""

    job_id: str = Field(min_length=1)
    state: JobState = Field(default="SUCCEEDED")
    candidates: list[SearchCandidate] = Field(default_factory=list)
    metrics: SearchMetrics
    completed_at: str = Field(min_length=1)


class SearchJobCanceled(BaseModel):
    """검색 작업 취소 응답 모델."""

    job_id: str = Field(min_length=1)
    state: JobState = Field(default="CANCELED")
    message: str = Field(min_length=1)
