# svve-core

SVVE(Segmented Vector Voting & Expansion)는 벡터 검색을 빠르고 안정적으로 수행하기 위한 Python-Rust 하이브리드 코어 라이브러리입니다.  
Python 인터페이스는 사용 편의성을 제공하고, Rust 코어는 연산 성능과 메모리 효율을 담당합니다. 두 계층은 `PyO3`와 `maturin`으로 연결되며, 최종 산출물은 wheel(`.whl`) 형태로 배포됩니다.

## 프로젝트 목표

이 프로젝트는 벡터 검색 시스템을 서비스에 쉽게 붙이면서도, 실제 운영 환경에서 성능과 안정성을 함께 확보하는 것을 목표로 합니다.

- 외부 검색 엔진 의존 없이 사용할 수 있는 독립형 벡터 검색 코어 SDK 제공
- 대규모 트래픽에서도 응답 시간과 메모리 사용량이 급격히 흔들리지 않는 실행 특성 확보
- Python API의 사용성은 유지하고, 핵심 연산은 Rust로 옮겨 처리량과 효율을 개선
- 단일 코드베이스로 개발하고, wheel 배포 방식으로 설치·운영 복잡도를 낮춤
- 장기적으로 확장 가능한 모듈 구조(api/core/index/math) 위에서 기능 고도화

## 기술적 기반

이 프로젝트는 단일 임베딩 벡터를 입력받아, 외부 검색 엔진 없이도 고정밀 Top-K 검색 결과를 반환하는 파이프라인을 구현합니다.
핵심은 `후보군 빠른 축소(Tier1)`와 `정밀 재검색(Tier2)`을 분리해 정확도와 성능을 함께 확보하는 것입니다.

검색 처리 흐름은 아래 순서로 동작합니다.

1. 서버 시작 시 `SearchEngine`이 인덱스를 한 번 로드합니다.
2. Tier1(BQ)·Tier2(Float32) 인덱스는 `memmap2`로 mmap 매핑되어 프로세스 간 메모리 공유를 유도합니다.
3. Python 계층에서 입력 벡터를 `numpy.float32` 1D 형태로 검증합니다.
4. `PyO3` 브릿지로 NumPy 데이터를 Rust로 전달하고, 검색 구간에서는 GIL 영향을 최소화합니다.
5. Rust 코어가 쿼리를 분할해 `rayon` 병렬 처리로 Tier1 해밍 검색을 수행합니다.
6. 분할 결과를 `hashbrown` 기반 투표로 집계해 생존 후보를 압축합니다.
7. 생존 후보의 Tier2 벡터로 centroid 확장을 수행한 뒤 최종 정밀 스코어링을 실행합니다.
8. 결과는 객체 리스트 대신 `(doc_ids, scores)` 형태의 NumPy 배열 튜플(SoA)로 반환합니다.

운영 관점 설계 원칙은 다음과 같습니다.

- 멀티프로세스 확장은 Python 서버 워커가 담당하고, Rust는 프로세스를 직접 관리하지 않습니다.
- CPU 집약 연산은 Rust 동기 함수 + `rayon` 스레드 풀로 처리하고, 불필요한 async 런타임은 사용하지 않습니다.
- 인덱스 상태는 `Arc` 기반 읽기 전용으로 공유해 락 경합을 최소화합니다.

## 디렉토리 구조

```text
.
├── docs/arch/blueprint.md
├── pyproject.toml
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── api/
│   ├── core/
│   ├── index/
│   └── math/
├── svve_core/
│   ├── __init__.py
│   ├── engine.py
│   ├── schemas.py
│   └── exceptions.py
└── tests/
    ├── python/
    │   └── test_schemas.py
    └── rust/
        └── main.rs
```

## 의존성

Python(runtime):

- `numpy`
- `pydantic`

Python(dev):

- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-env`
- `ruff`

Rust(runtime):

- `pyo3` (`abi3-py38`, `extension-module`)
- `numpy` (Rust crate)
- `rayon`
- `memmap2`
- `hashbrown`
- `ndarray`
- `bytemuck`

Rust(test):

- `rstest`

## 개발 시작

사전 조건:

- `uv` 설치
- Rust toolchain 설치 (`cargo`, `rustc`)

의존성 설치:

```bash
uv sync --dev
```

Rust 컴파일 확인:

```bash
cargo check
```

wheel 빌드:

```bash
uv build --wheel
```

## 테스트 방식

Python 테스트(`pytest`):

- 위치: `tests/python`
- 실행:

```bash
uv run pytest
```

Rust 테스트(`cargo test` + `rstest`):

- 위치: `tests/rust`
- 엔트리: `tests/rust/main.rs` (`Cargo.toml`의 `[[test]]`로 등록)
- 실행:

```bash
cargo test --test rust_tests
```

전체 Rust 테스트:

```bash
cargo test
```

참고:

- `pytest` 실행 시 `PYTHONDONTWRITEBYTECODE=1`이 설정되어 `__pycache__` 생성을 방지합니다.

## 패키징

- 빌드 백엔드: `maturin`
- Rust 확장 모듈 경로: `svve_core._svve_core`
- 배포 산출물 예시: `target/wheels/svve_core-0.1.0-...whl`
