# Vtree Search 런타임 동작 문서 (Phase 2)

## 1. 개요

본 문서는 라이브러리 모드에서 실제 동작하는 실행 경로를 설명한다.

- 공개 클래스: `VtreeIngestor`, `VTreeSearchEngine`
- 큐: Redis Streams
- DB: PostgreSQL (`pgvector`, `ltree`)

## 2. 검색 실행 시퀀스

1. `submit_search(query_text, query_embedding, top_k)` 호출
2. 큐 포화 검사
   - `depth >= QUEUE_REJECT_AT`면 즉시 거절
3. `job:{id}` 상태 해시 생성(`PENDING`)
4. Stream(`search:jobs`)에 메시지 enqueue
5. 워커(`run_worker_once`/`run_worker_forever`)가 메시지 소비
6. 상태 `RUNNING` 전환 후 Rust 검색 파이프라인 실행
7. 성공 시 `SUCCEEDED` + `result_json` 저장 + ACK
8. 실패 시 재시도 또는 DLQ 이동 후 ACK

## 3. 적재 실행 시퀀스

- `VtreeIngestor.upsert_document()`
  - summary/page 노드 업서트
- `VtreeIngestor.upsert_pages()`
  - page 노드만 업서트
- `VtreeIngestor.rebuild_summary_embeddings()`
  - summary 노드 갱신 트리거 실행
- `VtreeIngestor.build_page_nodes_from_path()`
  - Markdown/PDF/DOCX 파싱
  - PDF 표/이미지, DOCX 표 주석 본문 생성
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
- `filter_http_latency_ms`
- `filter_http_error_rate`

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
