# Vtree Search 런타임 동작 문서 (Phase 3)

## 관련 문서

- [프로젝트 개요](../../README.md)
- [아키텍처 청사진](./blueprint.md)
- [이론 배경](./theoretical_background.md)
- [운영 가이드](../ops/queueing-and-slo.md)
- [Python LLM 주입](../python/llm_injection.md)

## 1. 개요

본 문서는 라이브러리 모드에서 실제 동작하는 실행 경로를 설명한다.

- 공개 클래스: `VtreeIngestor`, `VTreeSearchEngine`
- 큐: Redis Streams
- DB: PostgreSQL (`pgvector`, `ltree`)
- LLM: Python 주입 LangChain 객체(`ainvoke`)

## 2. 검색 실행 시퀀스

1. `submit_search(query_text, query_embedding, top_k)` 호출
2. 큐 포화 검사
   - `depth >= QUEUE_REJECT_AT`면 즉시 거절
3. `job:{id}` 상태 해시 생성(`PENDING`)
4. Stream(`search:jobs`)에 메시지 enqueue
5. 워커(`await run_worker_once`/`await run_worker_forever`)가 메시지 소비
6. 상태 `RUNNING` 전환 후 Rust 검색 파이프라인 실행
7. Rust 확장 후보에 대해 LangChain 배치 필터(`ainvoke`) 실행
8. 성공 시 `SUCCEEDED` + `result_json` 저장 + ACK
9. 실패 시 재시도 또는 DLQ 이동 후 ACK

## 3. 적재 실행 시퀀스

- `await VtreeIngestor.upsert_document()`
  - summary/page 노드 업서트
- `await VtreeIngestor.upsert_pages()`
  - page 노드만 업서트
- `await VtreeIngestor.rebuild_summary_embeddings()`
  - summary 노드 갱신 트리거 실행
- `await VtreeIngestor.build_page_nodes_from_path()`
  - Markdown/PDF/DOCX 파싱
  - PDF 표/이미지, DOCX 표를 LLM 주석 생성
  - 레이아웃 메타데이터 포함 page 노드 변환

## 4. 잡 상태 머신

- `PENDING` -> `RUNNING` -> `SUCCEEDED`
- `PENDING` -> `RUNNING` -> `FAILED`
- `PENDING`/`RUNNING` -> `CANCELED`

## 5. 운영 지표

필수 수집 지표:

- `queue_depth`
- `queue_reject_count`
- `job_retry_count`
- `dlq_count`
- `job_latency_ms`
- `db_query_latency_ms`
- `search_llm_filter_latency_ms`
- `search_llm_filter_error_rate`
- `ingestion_llm_annotation_latency_ms`
- `ingestion_llm_annotation_error_rate`

## 6. 서비스 레벨 목표(초기값)

- 제출 응답 p95 <= 500ms
- 제출~완료 p95 <= 4s
- 큐 거절 비율 < 2%

## 7. 예외/오류 전달

- 포화: `QueueOverloadedError`
- 잡 없음: `JobNotFoundError`
- TTL 만료: `JobExpiredError`
- 실행 실패: `JobFailedError`
- 의존성 없음: `DependencyUnavailableError`
