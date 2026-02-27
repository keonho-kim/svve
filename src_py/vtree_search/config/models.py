"""
목적:
- Vtree Search 라이브러리의 설정 계약을 정의한다.

설명:
- Postgres/Redis/필터 HTTP/워커 제어 값을 단일 모델로 관리한다.
- `.env` 파싱은 드라이버 코드에서 수행하고 본 모델은 값 검증만 담당한다.

디자인 패턴:
- 값 객체(Value Object).

참조:
- scripts/run-search.py
- src_py/vtree_search/search/engine.py
- src_py/vtree_search/ingestion/ingestor.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PostgresConfig(BaseModel):
    """Postgres 연결 및 테이블 설정 모델."""

    dsn: str = Field(min_length=1)
    summary_table: str = Field(min_length=1)
    page_table: str = Field(min_length=1)
    embedding_dim: int = Field(ge=1)
    pool_min: int = Field(default=1, ge=1)
    pool_max: int = Field(default=8, ge=1)
    connect_timeout_ms: int = Field(default=2_000, ge=1)
    statement_timeout_ms: int = Field(default=3_000, ge=1)

    @field_validator("pool_max")
    @classmethod
    def validate_pool_max(cls, value: int, info) -> int:
        pool_min = info.data.get("pool_min", 1)
        if value < pool_min:
            raise ValueError("pool_max는 pool_min 이상이어야 합니다")
        return value


class RedisQueueConfig(BaseModel):
    """Redis Streams 큐 제어 설정 모델."""

    url: str = Field(min_length=1)
    stream_search: str = Field(default="search:jobs", min_length=1)
    stream_search_dlq: str = Field(default="search:jobs:dlq", min_length=1)
    consumer_group: str = Field(default="vtree-search-group", min_length=1)
    queue_max_len: int = Field(default=200, ge=1)
    queue_reject_at: int = Field(default=180, ge=1)
    result_ttl_sec: int = Field(default=900, ge=1)
    worker_block_ms: int = Field(default=1_000, ge=1)

    @field_validator("queue_reject_at")
    @classmethod
    def validate_reject_threshold(cls, value: int, info) -> int:
        queue_max_len = info.data.get("queue_max_len", 200)
        if value > queue_max_len:
            raise ValueError("queue_reject_at은 queue_max_len 이하이어야 합니다")
        return value


class FilterHttpConfig(BaseModel):
    """외부 필터 HTTP 엔드포인트 설정 모델."""

    url: str = Field(min_length=1)
    timeout_ms: int = Field(default=1_000, ge=1)
    auth_token: str | None = Field(default=None)
    model: str | None = Field(default=None)


class SearchConfig(BaseModel):
    """검색 엔진 설정 모델."""

    postgres: PostgresConfig
    redis: RedisQueueConfig
    filter_http: FilterHttpConfig
    worker_concurrency: int = Field(default=4, ge=1)
    max_retries: int = Field(default=3, ge=0)
    retry_base_ms: int = Field(default=200, ge=1)
    retry_max_ms: int = Field(default=2_000, ge=1)
    entry_limit: int = Field(default=3, ge=1)
    page_limit: int = Field(default=50, ge=1)

    @field_validator("retry_max_ms")
    @classmethod
    def validate_retry_window(cls, value: int, info) -> int:
        retry_base_ms = info.data.get("retry_base_ms", 200)
        if value < retry_base_ms:
            raise ValueError("retry_max_ms는 retry_base_ms 이상이어야 합니다")
        return value


class IngestionAnnotationConfig(BaseModel):
    """적재 주석(이미지/표) HTTP 엔드포인트 설정 모델."""

    url: str = Field(min_length=1)
    timeout_ms: int = Field(default=2_000, ge=1)
    auth_token: str | None = Field(default=None)
    model: str | None = Field(default=None)


class IngestionPreprocessConfig(BaseModel):
    """파일 전처리/청킹 설정 모델."""

    max_chunk_chars: int = Field(default=1_024, ge=256)
    sample_per_extension: bool = Field(default=False)
    enable_table_annotation: bool = Field(default=True)
    enable_image_annotation: bool = Field(default=True)
    asset_output_dir: str = Field(default="data/ingestion-assets", min_length=1)


class IngestionConfig(BaseModel):
    """적재 엔진 설정 모델."""

    postgres: PostgresConfig
    preprocess: IngestionPreprocessConfig = Field(default_factory=IngestionPreprocessConfig)
    annotation: IngestionAnnotationConfig | None = Field(default=None)
