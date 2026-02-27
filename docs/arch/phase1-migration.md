# Phase 1 전환 내역

## 1. 목적

SVVE 기반 구조에서 Vtree Search 구조로 전환하며, 2차 구현 시작 전 필요한 기반을 고정한다.

## 2. 적용된 변경

- 프로젝트 식별자 전환
  - `svve-core` -> `vtree-search`
  - `svve_core` -> `vtree_search`
  - `_svve_core` -> `_vtree_search`
- 소스 루트 분리
  - Python: `src_py/vtree_search`
  - Rust: `src_rs`
- 기존 SVVE 런타임 코드 제거
- 기존 문서 전면 교체
- `new-design.md` 내용을 아키텍처 문서로 통합 후 원본 삭제
- CI 자동 실행 임시 중단

## 3. 의도적 비구현 항목

- PostgreSQL 실연동 쿼리
- Rust 병렬 필터 실행
- LLM 실제 호출
- 실서비스용 테스트 시나리오

위 항목은 2차 구현 범위로 이월한다.

## 4. 안전한 이월 근거

- 경계 인터페이스와 오류 시맨틱이 이미 고정되어 있어, 런타임 로직만 순차 구현 가능하다.
- 문서/설정/디렉토리 식별자가 일치하므로 대규모 리네이밍 재작업이 필요 없다.

## 5. 2차 시작 체크리스트

- `src_py/vtree_search/retrieval/service.py` 구현 시작
- `src_rs/api/retrieval_bridge.rs`에서 실제 Rust 경로 호출 연결
- `src_rs/core/index/math` 모듈 단위 테스트 추가
- CI 빌드/테스트 파이프라인 재활성화
