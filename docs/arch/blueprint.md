# Segmented Vector Voting & Expansion (SVVE) 고속 검색 오케스트레이션 설계서 (Python-Rust Hybrid SDK)

## 1. 시스템 개요

본 프로젝트는 기존 Vector Database(VDB)와 연동해, 검색 시점의 처리 방식을 최적화함으로써 응답 성능과 검색 품질을 높이는 Python 패키지(`svve_core`)를 목표로 한다.

핵심 전제는 다음과 같다.

- 문서 임베딩은 이미 VDB에 적재되어 있다.
- 단일 임베딩 모델만 사용한다.
- 오프라인 사전 계산(특수 변환 행렬, 별도 보조 인덱스 생성)은 두지 않는다.
- 이중 인덱싱 없이, 단일 VDB 인덱스를 기반으로 동작한다.
- 연동 방식은 `search_fn` 콜백 주입 방식으로 외부 VDB와 연동한다.
- SVVE 알고리즘은 고정 절차(분할 검색 -> 투표 생존 -> PRF 보정 -> 확장 후 재검색/재정렬)로 동작한다.
- PRF(의사 관련피드백) 단계는 필수이며 생략하지 않는다.

즉, SVVE는 "인덱스 구조를 새로 만드는 엔진"이 아니라, 기존 VDB 위에서 런타임 질의 오케스트레이션을 수행하는 가속 레이어다.

## 2. 동시성 제어 및 상태 관리 아키텍처

### 멀티프로세싱 (Multi-processing): Python 위임

Rust 코어 내부에서 프로세스를 포크하거나 워커를 직접 관리하지 않는다.  
프로세스 확장(예: Gunicorn/Uvicorn)은 Python 애플리케이션 레이어가 담당한다.

### 멀티쓰레딩 (Multi-threading): Rust Rayon 기반 병렬 집계

Rust는 다음과 같은 CPU 집약 단계에 병렬 처리를 적용한다.

- 분할 질의 계획 생성
- 다중 검색 결과 병합
- 투표 집계 및 Top-K 선택

`rayon` 워크스틸링 스레드풀을 사용해 작업 편차를 흡수하고 꼬리 지연시간(p99)을 안정화한다.

### VDB 요청 동시 처리 원칙

VDB 호출은 `search_fn` 콜백 어댑터 경로로 수행한다.

- Python `search_fn` 콜백 어댑터: Python 콜백 호출 안정성을 위해 세그먼트 질의를 순차 실행

핵심은 "VDB 호출 정책"과 "CPU 집계 병렬성"을 분리해 관리하는 것이다.

### Lock-Free 상태 유지형(Stateful) 객체 설계

SDK 내부 `SearchEngine`(`#[pyclass]`) 객체는 프로세스당 1회 초기화한다.  
Rust 내부 상태(설정, 인덱스 식별자, 클라이언트 핸들)는 `Arc` 기반 읽기 중심 구조로 관리한다.

검색 경로에서는 공유 상태 변경을 최소화해 락 경합을 줄인다.

## 3. 배포 및 소스코드 보호 전략

작성된 코드는 소스코드가 아닌 네이티브 바이너리 휠(`.whl`) 형태로 배포한다.

- **바이너리 컴파일:** `maturin`으로 Rust 확장 모듈(`.so`, `.pyd`) 생성
- **IP 보호:** 배포 패키지에 핵심 Rust 소스 미포함
- **릴리즈 최적화:** `LTO(fat)`, `strip = true` 기반 빌드
- **설치 편의성:** 사용자 환경에 Rust가 없어도 `pip install ...whl`로 설치 가능

## 4. 엔터프라이즈급 모듈화 디렉토리 구조

장기 유지보수를 위해 Python 인터페이스 계층과 Rust 실행 계층을 분리한다.

```text
svve_project/
├── pyproject.toml
├── Cargo.toml
├── README.md
│
├── svve_core/                  (Python 인터페이스 계층)
│   ├── __init__.py
│   ├── engine.py               (사용자 API, Rust 객체 호출)
│   ├── schemas.py              (입력 검증)
│   └── exceptions.py           (예외 표준화)
│
└── src/                        (Rust 실행 계층)
    ├── lib.rs                  (PyO3 진입점)
    │
    ├── api/
    │   └── search_engine.rs    (SearchEngine 상태/FFI 경계)
    │
    ├── core/
    │   ├── pipeline.rs         (검색 전체 흐름 제어)
    │   ├── voting.rs           (결과 병합/투표 로직)
    │   └── expansion.rs        (필수 PRF 쿼리 보정/재검색 제어)
    │
    ├── vdb/
    │   ├── adapter.rs          (VDB 클라이언트 추상화)
    │   ├── query.rs            (분할 질의 생성/전송)
    │   └── fetch.rs            (후보 벡터/메타데이터 조회)
    │
    └── math/
        ├── linalg.rs           (내적/유사도 계산)
        ├── normalize.rs        (벡터 정규화)
        └── topk.rs             (Top-K 선택/정렬 유틸)
```

## 5. 필수 라이브러리 및 기술 스택 명세

### Python 생태계 (pyproject.toml)

- **numpy:** 벡터 입출력 표준 배열 타입
- **pydantic:** 요청 입력 형상/타입 검증

### Rust 환경 (Cargo.toml)

- **pyo3:** Python-Rust FFI 브릿지
- **rust-numpy:** NumPy 배열 무복사 뷰 연동
- **rayon:** 병렬 집계/정렬 처리
- **hashbrown:** 고성능 해시 집계(투표/병합)
- **ndarray:** 선형대수/배열 연산
- **bytemuck:** 저비용 데이터 캐스팅 유틸
- **(선택) VDB SDK:** 대상 VDB에 맞는 클라이언트 라이브러리
- **PyO3 콜백 브릿지:** `search_fn(query, top_k)` 호출 경로 지원

## 6. 데이터 플로우 및 실행 시나리오 (Online Inference)

1. **서버 기동 및 상태 초기화**
   `SearchEngine`을 생성하고, 요청 시 `search_fn`을 주입할 준비 상태를 만든다.
2. **쿼리 수신 및 검증 (Python)**
   외부 임베딩 모델이 생성한 `numpy.float32` 1D 벡터를 입력받아 검증한다.
3. **FFI 진입 (PyO3)**
   NumPy 데이터를 Rust로 전달하고 검색 파이프라인을 시작한다.  
   호출 경로는 `search(query, top_k, search_fn)` 단일 경로를 사용한다.
4. **분할 질의 생성 및 병렬 검색 (고정)**
   쿼리를 4개 세그먼트 질의로 고정 분할하고(`N=4`), 세그먼트별 Top-100(`k_seg=100`)을 요청한다.  
   - 실행 정책: Python `search_fn` 콜백 안정성을 위해 순차 실행
5. **투표 기반 후보 병합 및 생존 선택 (고정)**
   문서 ID 기준으로 집계하고 투표 규칙을 고정 적용한다.
   - 3표 이상: Strong Candidate
   - 2표: Weak Candidate
   - 1표: Noise로 제거
   생존 문서는 상위 5개(`M=5`)로 고정한다.
6. **쿼리 보정(PRF) 및 재검색 (필수)**
   생존 후보 벡터 중심으로 `q* = 0.7q + 0.3c`를 계산하고(`alpha=0.7` 고정), 보정 쿼리 `q*`로 재검색을 수행한다.
7. **Top-K 충족 반복 (고정)**
   추가 검색과 후보 재정렬을 반복한다. 종료 조건은 다음 중 하나다.
   - 최종 결과 개수가 요청 `top_k`를 충족
   - 조기 종료 조건 충족(랭킹 안정화)
   - 최대 반복 라운드 도달
8. **최종 Top-K 반환**
   결과를 `(doc_ids, scores)` SoA 형태의 NumPy 배열로 반환한다.

### 6.1 고정 수치 목표

- 세그먼트 수: `N=4`
- 세그먼트별 1차 검색 후보: `k_seg=100`
- 생존 후보 수: `M=5`
- PRF 계수: `alpha=0.7`, `1-alpha=0.3`
- 운영 지연시간 목표: `p95 <= 100ms`, `p99 <= 150ms` (CPU 기준)
- 조기 종료 임계치: Jaccard `>= 0.95`, 점수 개선율 `<= 0.5%`, 연속 2라운드
- 최대 반복 라운드: `MAX_REFINEMENT_ROUNDS=8`

## 7. 비목표 및 설계 제한

- 인덱스 오프라인 빌더/재학습 파이프라인은 이 설계 범위에 포함하지 않는다.
- 별도 보조 인덱스, 사전 변환 행렬 저장소, 이중 검색 계층은 기본 구성에서 사용하지 않는다.
- 단일 임베딩 모델을 기준으로 인터페이스와 런타임 로직을 단순화한다.
