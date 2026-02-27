# Rust 모듈 레퍼런스 (Phase 2)

## `src_rs/lib.rs`

- PyO3 모듈 엔트리: `_vtree_search`
- 노출 클래스: `SearchBridge`, `IngestionBridge`

## `src_rs/api/search_bridge.rs`

- 클래스: `PySearchBridge`
- 메서드:
  - `new()`
  - `status() -> String`
  - `execute(payload_json: &str) -> PyResult<String>`

## `src_rs/api/ingestion_bridge.rs`

- 클래스: `PyIngestionBridge`
- 메서드:
  - `new()`
  - `status() -> String`
  - `execute(payload_json: &str) -> PyResult<String>`

## `src_rs/core/errors.rs`

- `CoreError`
  - `InvalidInput`
  - `InvalidConfig`
  - `Db`
  - `Http`
  - `Serialization`
  - `Runtime`

## `src_rs/core/search_pipeline.rs`

- 입력: `SearchRequestPayload`
- 출력: `SearchResultPayload`
- 함수: `execute_search(payload)`

## `src_rs/core/ingestion_pipeline.rs`

- 입력: `IngestionRequestPayload`
- 출력: `IngestionResultPayload`
- 함수: `execute_ingestion(payload)`

## `src_rs/core/filter_http.rs`

- `FilterHttpClient`
- 함수:
  - `filter_candidates(question, candidates, concurrency)`

## `src_rs/index/postgres_repo.rs`

- `PostgresRepository`
- 함수:
  - `search_summary_nodes()`
  - `fetch_pages_under_path()`
  - `upsert_summary_nodes()`
  - `upsert_page_nodes()`
  - `touch_summary_nodes()`

## `src_rs/index/sql.rs`

- `validate_identifier(value, field_name)`
- `to_pgvector_literal(values)`
