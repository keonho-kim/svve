# Rust 모듈/함수 레퍼런스

## 1) `src/lib.rs`

### 역할

- PyO3 모듈 엔트리포인트
- 하위 Rust 모듈 트리 선언

### 식별자

| 식별자 | 시그니처 | 설명 |
|---|---|---|
| `_svve_core` | `fn _svve_core(m: &Bound<'_, PyModule>) -> PyResult<()>` | Python 확장 모듈 초기화. `PySearchEngine` 클래스를 export한다. |

## 2) `src/api/search_engine.rs`

### 역할

- Python-Rust FFI 경계
- 쿼리 배열 레이아웃 검사
- `search_fn` 기반 어댑터 생성 후 코어 파이프라인 호출

### 타입/함수

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `PySearchEngine` | `#[pyclass] struct` | Python에서 보이는 검색 엔진 객체 | 없음 |
| `new` | `pub fn new() -> Self` | 상태 없는 Rust 검색 엔진 객체 생성 | 없음 |
| `search` | `pub fn search(&self, query: PyReadonlyArray1<'_, f32>, top_k: usize, search_fn: Py<PyAny>) -> PyResult<(Vec<u32>, Vec<f32>)>` | 입력 검증 후 `pipeline::execute_search` 실행 | 비연속 배열, Rust 파이프라인 에러 |

## 3) `src/core/pipeline.rs`

### 역할

- 고정 검색 절차 오케스트레이션
- 각 단계의 실패를 명시적 에러 문자열로 전달

### 함수

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `execute_search` | `pub fn execute_search(adapter: &dyn VdbAdapter, query: &[f32], top_k: usize) -> Result<(Vec<u32>, Vec<f32>), String>` | `정규화 -> 세그먼트 검색 -> 투표 -> PRF -> 재검색/재정렬` 전체 흐름 실행 | `top_k=0`, 빈 쿼리, 차원 불일치, 0-벡터, 생존 후보 없음, 최종 결과 없음 |

## 4) `src/core/voting.rs`

### 역할

- 세그먼트 검색 결과 병합
- 3/2/1 규칙 기반 후보 분류
- 생존 후보 선별

### 타입/함수

| 식별자 | 시그니처 | 설명 | 비고 |
|---|---|---|---|
| `VoteClass` | `pub enum VoteClass { Strong, Weak, Noise }` | 투표 강도 분류 | 3+, 2, 1 이하 |
| `VoteRecord` | `pub struct VoteRecord` | 문서별 집계 레코드(`votes`, `rank_score`, `best_score`) | 정렬 기준 입력 |
| `merge_segment_results` | `pub fn merge_segment_results(segment_results: &[Vec<ScoredDoc>]) -> Vec<VoteRecord>` | 문서 ID 기준 집계 후 우선순위 정렬 | 정렬: votes -> rank_score -> best_score -> doc_id |
| `classify_vote` | `pub fn classify_vote(votes: u8) -> VoteClass` | 투표 수를 등급으로 변환 | 고정 규칙 |
| `select_survivor_ids` | `pub fn select_survivor_ids(records: &[VoteRecord], limit: usize) -> Vec<DocId>` | Noise 제외 후 상위 후보 ID 반환 | `SURVIVOR_COUNT`와 함께 사용 |

## 5) `src/core/expansion.rs`

### 역할

- PRF 보정 쿼리 계산
- 라운드 기반 재검색/재정렬
- 조기 종료 판단

### 공개 함수

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `build_prf_query` | `pub fn build_prf_query(original_query: &[f32], survivors: &[DocId], adapter: &dyn VdbAdapter) -> Result<Vec<f32>, String>` | 생존 문서 centroid를 이용해 `q* = alpha*q + (1-alpha)*c` 계산 후 정규화 | 생존 후보 비어있음, 벡터 fetch/차원 오류, 0-벡터 |
| `rerank_until_top_k` | `pub fn rerank_until_top_k(adapter: &dyn VdbAdapter, prf_query: &[f32], top_k: usize) -> Result<Vec<ScoredDoc>, String>` | 라운드마다 limit 확장 검색, 중복 병합, Top-K 안정화 기준으로 종료 | adapter 검색 실패 |

### 내부 함수(변경 시 영향 큼)

| 식별자 | 설명 |
|---|---|
| `top_k_from_merged` | 병합 맵을 Top-K 정렬 결과로 변환 |
| `jaccard_similarity` | 연속 라운드 Top-K 집합 유사도 계산 |
| `relative_score_improvement` | 연속 라운드 점수 합 개선율 계산 |

## 6) `src/vdb/adapter.rs`

### 역할

- 외부 VectorDB 연동 인터페이스 정의
- Python `search_fn` 콜백 기반 기본 구현(`CallbackVdb`) 제공

### 타입/트레이트

| 식별자 | 시그니처 | 설명 |
|---|---|---|
| `DocId` | `pub type DocId = u32` | 문서 ID 타입 |
| `ScoredDoc` | `pub type ScoredDoc = (DocId, f32)` | 검색 hit 타입 |
| `DocVector` | `pub struct DocVector { id, vector }` | PRF용 원본 벡터 페이로드 |
| `VdbAdapter` | `pub trait VdbAdapter` | `dim/search/fetch_vectors` 3개 메서드 계약 |
| `CallbackVdb` | `pub struct CallbackVdb` | Python 콜백 어댑터 + 벡터 캐시 |

### 주요 함수

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `CallbackVdb::new` | `pub fn new(search_fn: Py<PyAny>, dim: usize) -> Self` | 콜백/차원/캐시 초기화 | 없음 |
| `search` | `fn search(&self, query: &[f32], limit: usize) -> Result<Vec<ScoredDoc>, String>` | `search_fn(query, limit)` 호출, `(ids,scores,vectors)` 검증/정규화/캐시 저장 | 차원/길이 불일치, 콜백 예외, 0-벡터, 캐시 잠금 실패 |
| `fetch_vectors` | `fn fetch_vectors(&self, doc_ids: &[DocId]) -> Result<Vec<DocVector>, String>` | 캐시에서 PRF 대상 벡터 조회 | 캐시 미존재, 잠금 실패 |

## 7) `src/vdb/query.rs`

### 역할

- 세그먼트 분할 기준과 고정 상수 관리
- 세그먼트용 투영 쿼리 생성

### 타입/상수/함수

| 식별자 | 종류 | 설명 |
|---|---|---|
| `SegmentRange` | `struct` | 세그먼트 구간 `[start, end)` |
| `SEGMENT_COUNT` | `const usize = 4` | 세그먼트 수 |
| `SEGMENT_TOP_K` | `const usize = 100` | 세그먼트별 후보 수 |
| `SURVIVOR_COUNT` | `const usize = 5` | 생존 후보 수 |
| `PRF_ALPHA` | `const f32 = 0.7` | PRF 원본 쿼리 가중치 |
| `MAX_REFINEMENT_ROUNDS` | `const usize = 8` | 최대 재검색 라운드 |
| `segment_ranges` | `pub fn segment_ranges(dim: usize) -> Vec<SegmentRange>` | 차원을 4개 구간으로 균등 분할 |
| `build_segment_query` | `pub fn build_segment_query(query: &[f32], segment: SegmentRange) -> Vec<f32>` | 해당 구간만 남긴 투영 쿼리 생성 |

## 8) `src/vdb/fetch.rs`

### 역할

- adapter 벡터 조회 래핑
- 생존 후보 centroid 계산

### 함수

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `fetch_vectors` | `pub fn fetch_vectors(adapter: &dyn VdbAdapter, doc_ids: &[DocId]) -> Result<Vec<DocVector>, String>` | adapter 호출 위임 | adapter 오류 |
| `centroid` | `pub fn centroid(vectors: &[DocVector], dim: usize) -> Result<Vec<f32>, String>` | 평균 벡터 계산 | 빈 입력, 차원 불일치 |

## 9) `src/math/linalg.rs`

### 역할

- 기본 선형대수 유틸

### 함수

| 식별자 | 시그니처 | 설명 |
|---|---|---|
| `dot` | `pub fn dot(left: &[f32], right: &[f32]) -> f32` | 두 벡터 내적 |
| `l2_norm` | `pub fn l2_norm(values: &[f32]) -> f32` | L2 노름 |
| `normalize_in_place` | `pub fn normalize_in_place(values: &mut [f32]) -> Option<()>` | 제자리 정규화, 0-벡터면 `None` |

## 10) `src/math/normalize.rs`

### 역할

- 복사 기반 안전 정규화 래퍼

### 함수

| 식별자 | 시그니처 | 설명 |
|---|---|---|
| `normalized_copy` | `pub fn normalized_copy(values: &[f32]) -> Option<Vec<f32>>` | 입력을 복사해 정규화, 실패 시 `None` |

## 11) `src/math/topk.rs`

### 역할

- 점수 기반 정렬 및 상위 K개 절단

### 함수

| 식별자 | 시그니처 | 설명 |
|---|---|---|
| `sort_desc_take` | `pub fn sort_desc_take(scored: &mut Vec<ScoredDoc>, top_k: usize)` | 점수 내림차순 + ID 오름차순 정렬 후 `top_k`로 truncate |
| `compare_scored_doc` | `fn compare_scored_doc(left: &ScoredDoc, right: &ScoredDoc) -> Ordering` | 내부 비교 함수 |

## 12) 변경 영향도 빠른 가이드

- `vdb/query.rs` 상수 변경: 검색 품질/지연시간/문서(`docs/arch/*`)에 직접 영향.
- `vdb/adapter.rs` 반환 계약 변경: Python `search_fn` 구현체와 호환성 영향.
- `core/expansion.rs` 조기 종료 조건 변경: 결과 안정화/라운드 수 영향.
- `api/search_engine.rs` 시그니처 변경: Python API 호환성 영향.
