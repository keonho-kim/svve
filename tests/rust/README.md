# Rust 테스트 안내

## 목적
- `src_rs` 코어 파이프라인 통합 테스트 위치를 정의한다.

## 권장 범위
- 검색 파이프라인 SQL 경로
- 적재 upsert 경로
- 필터 HTTP 오류/타임아웃 경로
- JSON 인터페이스 파싱 실패 경로

## 실행 핸드오프
- `cargo test --test rust_tests`
