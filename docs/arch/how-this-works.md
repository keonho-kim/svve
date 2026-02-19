# Segmented Vector Voting & Expansion (SVVE) 실제 동작 문서

## 1. 문서 목적

이 문서는 SVVE 라이브러리가 "이미 구축된 VDB"와 연동되어 실제 런타임에서 어떻게 동작하는지 설명한다.  
이론 배경은 `docs/arch/theoretical_background.md`, 전체 설계 기준은 `docs/arch/blueprint.md`를 따른다.

## 2. 런타임 아키텍처 개요

SVVE는 세 계층으로 구성된다.

- Python 계층(`svve_core`): 입력 검증, 예외 표준화, 사용자 API
- Rust 계층(`src/*`): 고정 SVVE 절차 실행(분할, 투표, PRF, 재검색/재정렬)
- 외부 VDB: 실제 벡터 검색 저장소(이미 임베딩 완료 상태)

핵심 포인트:

- 단일 임베딩 모델만 사용
- 단일 VDB 인덱스만 사용
- 오프라인 사전 계산/별도 보조 인덱스 없음
- PRF 단계는 필수이며 항상 실행

## 3. 코드 구조와 실행 책임

| 경로 | 책임 |
|---|---|
| `svve_core/engine.py` | 사용자용 `SearchEngine` 래퍼, Rust 호출 |
| `svve_core/schemas.py` | 쿼리/파라미터 검증(Pydantic) |
| `svve_core/exceptions.py` | Python 계층 예외 타입 |
| `src/lib.rs` | PyO3 모듈 진입점, 클래스 export |
| `src/api/search_engine.rs` | Python-Rust 경계 객체(`#[pyclass]`) |
| `src/core/pipeline.rs` | 요청 단위 고정 파이프라인 오케스트레이션 |
| `src/core/voting.rs` | 3/2/1 투표 규칙 집계 |
| `src/core/expansion.rs` | 필수 PRF 보정 및 재검색 루프 |
| `src/vdb/*` | VDB 요청/응답 어댑터 계층(설계 기준) |
| `src/math/*` | 정규화/점수/Top-K 계산 유틸 |

## 4. 실제 처리 순서 (Online Inference)

### 4.1 서버 시작 (Startup)

1. 애플리케이션이 `SearchEngine(...)`을 초기화한다.
2. 엔진은 VDB 연결 정보(엔드포인트, 컬렉션/인덱스명)를 상태로 보관한다.
3. Rust 내부에서 병렬 처리 자원(`rayon` 스레드풀)을 준비한다.

### 4.2 요청 수신 및 검증 (Python)

1. 외부 임베딩 모델이 만든 1D 벡터를 입력받는다.
2. `schemas.py`에서 `numpy.float32` 1D 여부와 `top_k` 범위를 검증한다.
3. 실패 시 Python 예외로 즉시 응답한다.

### 4.3 Rust 고정 파이프라인 실행

1. PyO3 경계에서 NumPy 데이터를 Rust로 전달한다.
2. 쿼리를 4개 세그먼트 질의로 분할한다(`N=4`).
3. 세그먼트별 Top-100 후보를 병렬 검색한다(`k_seg=100`).
4. 문서 ID 기준으로 병합하고 3/2/1 투표 규칙을 적용한다.
5. 상위 생존 후보 5개를 확정한다(`M=5`).
6. 생존 후보 기반 PRF 보정 쿼리를 생성한다(`q* = 0.7q + 0.3c`).
7. 보정 쿼리로 추가 검색과 후보 재정렬을 반복한다.
8. 최종 결과 수가 요청 `top_k`를 채우면 루프를 종료한다.

### 4.4 응답 반환

응답은 SoA(Struct of Arrays) 형태로 반환한다.

- `doc_ids: np.ndarray[np.uint32]`
- `scores: np.ndarray[np.float32]`

객체 리스트 생성을 줄여 Python 레이어의 GC 부담을 낮춘다.

## 5. 공개 API 설계

공개 인터페이스는 단순하게 유지한다.

```python
from svve_core import SearchEngine

engine = SearchEngine(index_root="/path/or/alias")
ids, scores = engine.search(query, top_k=10)
```

### 입력 인터페이스

- `query`: 1차원 배열로 해석 가능해야 하며 내부에서 `float32`로 정규화
- `top_k`: 1 이상의 정수

### 출력 인터페이스

- 길이가 같은 `(ids, scores)` 배열 반환
- `ids`: 문서 식별자, `scores`: 최종 유사도/랭킹 점수

### 예외 인터페이스

- 입력 검증 실패: Python 검증 예외
- 실행 실패: Rust 오류를 Python 예외 메시지로 변환

## 6. 동시성 및 상태 관리 원칙

- 멀티프로세스 확장: Python 워커 레이어에서 담당
- CPU 병합/정렬: Rust `rayon` 병렬 처리
- VDB I/O 동시성: 어댑터 정책(동기 스레드 병렬 또는 비동기 호출)으로 분리
- 공유 상태: `Arc` 읽기 중심 구조로 락 경합 최소화

## 7. 고정 운영 목표

- 세그먼트 수: `N=4`
- 세그먼트별 후보 수: `k_seg=100`
- 생존 후보 수: `M=5`
- PRF 계수: `alpha=0.7`
- 지연시간 목표: `p95 <= 100ms`, `p99 <= 150ms`
- 완료 기준: 최종 결과가 요청 `top_k`를 충족할 때

## 8. 추가 최적화 항목 (절차 고정)

### 8.1 Python 계층

- `float32` contiguous fast path로 불필요한 배열 복사 제거
- 요청 핫패스에서 검증 비용 최소화
- 엔진 객체 재사용으로 cold start 및 초기화 비용 완화

### 8.2 Rust 계층(병렬)

- 전역 스레드풀 재사용(요청당 재생성 금지)
- 스레드 로컬 집계 후 병합으로 경합 감소
- partial top-k 사용으로 전체 정렬 비용 절감
- scratch buffer 재사용으로 힙 할당 부담 감소

### 8.3 VDB 계층

- 동시 요청 수 제한(concurrency cap) 적용
- 타임아웃/재시도/서킷브레이커 정책 분리
- 검색 실패 시 예외 인터페이스로 명시적 전파

## 9. 현재 구현 상태와 다음 단계

- 현재는 API/모듈/빌드 경로 중심의 골격이 준비된 상태다.
- 다음 단계는 `src/core/*`, `src/vdb/*`, `src/math/*`에 실제 런타임 로직을 채워  
  문서화된 고정 파이프라인과 구현을 1:1로 일치시키는 것이다.
