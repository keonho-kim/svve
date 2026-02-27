# Rust 계층 개요 (Phase 2)

## 목적

`src_rs`는 검색/적재 핵심 실행 경로를 담당한다.

## 모듈 책임

- `api/`
  - `SearchBridge`: 검색 JSON 실행 진입점
  - `IngestionBridge`: 적재 JSON 실행 진입점
- `core/`
  - `search_pipeline`: 검색 파이프라인
  - `ingestion_pipeline`: 적재 파이프라인
  - `filter_http`: 외부 필터 병렬 호출
  - `errors`: 오류 모델
- `index/`
  - `postgres_repo`: 조회/upsert 저장소
  - `sql`: 식별자/벡터 리터럴 검증 유틸
- `math/`
  - 점수 보정 유틸

## 운영 원칙

- DB 쿼리는 Rust에서 직접 수행
- 필터 HTTP는 Rust에서 병렬 실행
- 오류는 문자열이 아닌 구조적 타입(`CoreError`)으로 분류
