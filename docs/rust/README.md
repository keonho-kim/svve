# Rust 문서 개요

## 목적

이 문서는 `src/`의 Rust 코드베이스를 빠르게 파악하고 유지보수하기 위한 인덱스 문서다.  
기준은 "현재 `src/lib.rs`에 연결되어 실제로 빌드/실행되는 모듈"이다.

## 현재 활성 컴포넌트

```text
src/lib.rs
├── api/search_engine.rs
├── core/pipeline.rs
├── core/voting.rs
├── core/expansion.rs
├── vdb/adapter.rs
├── vdb/query.rs
├── vdb/fetch.rs
├── math/linalg.rs
├── math/normalize.rs
└── math/topk.rs
```

## 요청 처리 흐름 (핵심)

1. Python `SearchEngine.search(...)`가 PyO3 경계(`api/search_engine.rs`)로 들어온다.
2. `CallbackVdb`가 `search_fn`을 감싼 뒤 `core::pipeline::execute_search`를 호출한다.
3. 파이프라인은 쿼리 정규화 -> 세그먼트 검색 -> 투표 생존 -> PRF 보정 -> 재검색/재정렬 순서로 실행한다.
4. 최종 `(Vec<u32>, Vec<f32>)`를 Python으로 반환한다.

## 문서 목록

- `docs/rust/module_reference.md`: 모듈별/함수별 상세 레퍼런스

## 유지보수 체크리스트

- `pub fn`, `pub struct`, `pub trait`, `pub enum`를 추가/변경하면 `module_reference.md`를 함께 갱신한다.
- 검색 파이프라인 단계/상수(`SEGMENT_TOP_K`, `SURVIVOR_COUNT`, `PRF_ALPHA`, `MAX_REFINEMENT_ROUNDS`)를 바꾸면 `docs/arch/*`와 함께 동기화한다.
- Python-Rust 경계 시그니처(`PySearchEngine.search`, `CallbackVdb.search`)를 바꾸면 `docs/python/module_reference.md`도 같이 갱신한다.

## 참고: 현재 미연결 파일

현재 없음.
