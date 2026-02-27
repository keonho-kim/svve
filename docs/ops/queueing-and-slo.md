# Queueing & SLO 운영 가이드

## 관련 문서

- [프로젝트 개요](../../README.md)
- [아키텍처 청사진](../arch/blueprint.md)
- [런타임 동작](../arch/how-this-works.md)
- [이론 배경](../arch/theoretical_background.md)
- [Python 개요](../python/README.md)
- [Python LLM 주입](../python/llm_injection.md)

## 1. 큐 정책

- 모델: Redis Streams + Consumer Group
- 보장: At-least-once
- 상태 저장: `job:{id}` 해시 + TTL
- DLQ: `search:jobs:dlq`

## 2. 임계치 기본값

- `QUEUE_MAX_LEN=200`
- `QUEUE_REJECT_AT=180`
- `WORKER_CONCURRENCY=min(4, CPU)`
- `JOB_MAX_RETRIES=3`
- `JOB_RETRY_BASE_MS=200`
- `JOB_RETRY_MAX_MS=2000`

## 3. SLO 목표

- 제출 응답 p95 <= 500ms
- 제출~완료 p95 <= 4s
- 큐 거절 비율 < 2%

## 4. 장애 대응

### 큐 적체 증가

1. `queue_depth`, `queue_reject_count` 확인
2. `search_llm_filter_latency_ms` 확인
3. 필요 시 `QUEUE_REJECT_AT` 하향 또는 워커 수평 확장

### DLQ 증가

1. `dlq_count` 확인
2. `last_error` 패턴 분석
3. 원인 수정 후 DLQ 재처리 배치 실행

### DB 지연

1. `db_query_latency_ms` 확인
2. 인덱스 상태(`pgvector`, `ltree`) 점검
3. statement timeout 및 pool 설정 재조정

## 5. Ingestion 부하 제어

### 표/이미지 주석 비용 제어

1. 샘플 모드(`sample_per_extension=true`)로 문서 유형별 비용을 먼저 측정한다.
2. `enable_table_annotation`, `enable_image_annotation`을 독립 제어해 병목 원인을 분리한다.
3. `max_chunk_chars`를 과도하게 키우지 않아 단일 요청의 토큰 비용 폭증을 막는다.
4. `asset_output_dir` 디스크 사용량(용량/파일 수)을 주기적으로 점검한다.

### 권장 운영 지표

- `ingestion_files_total`
- `ingestion_tables_total`
- `ingestion_images_total`
- `ingestion_llm_annotation_latency_ms`
- `ingestion_llm_annotation_error_rate`
- `ingestion_asset_disk_usage_bytes`

## 6. Ingestion 장애 대응

### 주석 지연/실패 증가

1. `ingestion_llm_annotation_latency_ms`, `ingestion_llm_annotation_error_rate`를 확인한다.
2. 이미지/표 중 병목 모듈을 구분하기 위해 플래그를 분리 적용한다.
3. 필요 시 샘플 모드로 축소 실행 후 원인 문서 유형(PDF/DOCX)을 특정한다.

### 이미지 자산 급증

1. `asset_output_dir` 용량 증가 추세를 확인한다.
2. 재실행 정책(보존 기간/정리 주기)을 명시해 파일 누적을 제어한다.
3. 문서별 이미지 수가 과도한 경우 입력 문서 품질을 점검한다.
