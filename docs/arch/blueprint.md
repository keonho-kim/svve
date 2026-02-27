# Vtree Search 아키텍처 청사진 (Phase 2)

## 1. 목표

Vtree Search는 멀티모달 문서 검색에서 아래 목표를 달성한다.

- 벡터 숏컷 기반 빠른 엔트리 탐색
- 트리(`ltree`) 기반 문맥 확장
- 외부 필터 HTTP를 통한 노이즈 제거
- 큐잉 기반 부하 제어와 tail latency 보호

## 2. 시스템 경계

### 라이브러리가 담당하는 것

- Rust 검색/적재 파이프라인
- Python FFI 래퍼
- Python 공개 클래스
  - `VtreeIngestor`
  - `VTreeSearchEngine`
- Redis 큐잉/잡 상태/DLQ

### 라이브러리가 담당하지 않는 것

- HTTP 서버 구현
- 인증/인가
- 멀티테넌시 정책
- API 라우팅

## 3. 계층 책임

### Python (`src_py/vtree_search`)

- `config/`: 설정 계약
- `contracts/`: DTO/잡 상태 모델
- `runtime/`: Rust 브릿지 호출
- `queue/`: Redis Streams 관리
- `ingestion/`: `VtreeIngestor` + 멀티모달 파서(표/이미지 주석 포함)
- `search/`: `VTreeSearchEngine`

### Rust (`src_rs`)

- `api/`: `SearchBridge`, `IngestionBridge`
- `core/`: 검색/적재 파이프라인 + 필터 HTTP
- `index/`: Postgres 저장소 + SQL 검증 유틸
- `math/`: 점수 보정 유틸

## 4. 검색 데이터 플로우

1. 앱이 `submit_search()` 호출
2. Python이 입력 검증 후 Redis Stream에 job 추가
3. 워커가 job을 읽고 Rust `SearchBridge.execute()` 호출
4. Rust가 `pgvector` 엔트리 조회
5. Rust가 `ltree` 하위 페이지 확장
6. Rust가 필터 HTTP를 병렬 호출해 keep 판정
7. Rust가 top-k 후보 JSON 반환
8. Python이 `job:{id}` 해시에 결과 저장 후 ACK

## 5. 큐잉/부하 제어 규약

- 큐 모델: Redis Streams + Consumer Group
- 보장 모델: At-least-once
- 임계치:
  - `QUEUE_MAX_LEN=200`
  - `QUEUE_REJECT_AT=180`
- 재시도: 3회 지수 백오프
- DLQ: `search:jobs:dlq`
- 포화 시 즉시 거절: `QueueOverloadedError`

## 6. 저장소 계약

- DB: PostgreSQL + `pgvector` + `ltree`
- 테이블 기본 계약:
  - `summary_nodes(node_id, document_id, path, summary_text, embedding, metadata, updated_at)`
  - `page_nodes(node_id, parent_node_id, document_id, path, content, image_url, metadata, updated_at)`

## 7. 실패 시맨틱

- 입력 오류: `InvalidInput`/`ConfigurationError`
- 의존성 오류: `DependencyUnavailableError`
- 잡 실패: `JobFailedError`
- 큐 포화: `QueueOverloadedError`
- 결과 TTL 만료: `JobExpiredError`
