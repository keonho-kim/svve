# svve-core

SVVE(Segmented Vector Voting & Expansion)는 Python-Rust 하이브리드 벡터 검색 라이브러리입니다.
Python은 인터페이스를 제공하고, Rust는 고정 검색 파이프라인(분할 검색 -> 투표 -> PRF -> 재검색/재정렬)을 수행합니다.

## 핵심 포인트

- 단일 임베딩 모델에 기반한 시스템을 가정
- PRF(의사 관련피드백) 단계는 필수
- 결과는 `(ids, scores)` NumPy 배열(SoA)로 반환
- 외부 VectorDB 연동은 `search_fn` 주입 방식으로 수행

## 동작 개요

1. 쿼리를 4개 세그먼트(`N=4`)로 분할
2. 세그먼트별 후보 검색(`k_seg=100`)
3. 3/2/1 투표 규칙으로 생존 후보(`M=5`) 선택
4. PRF 보정 쿼리 생성 (`q* = 0.7q + 0.3c`)
5. 추가 검색/재정렬 반복
6. `top_k` 충족 또는 조기 종료 조건 충족 시 종료

조기 종료 조건:

- Top-K Jaccard `>= 0.95`
- 점수 개선율 `<= 0.5%`
- 위 조건 2라운드 연속 만족
- 최대 반복 라운드: `MAX_REFINEMENT_ROUNDS=8`

## 빠른 시작

사전 요구사항:

- `uv`
- Rust toolchain (`cargo`, `rustc`)

```bash
uv sync --dev
cargo check
uv build --wheel
```

## 사용 예시 (`search_fn` 필수)

```python
import numpy as np
from svve_core import SearchEngine


def search_fn(query: np.ndarray, top_k: int):
    # 외부 VDB 호출 결과를 아래 형식으로 반환
    # ids: list[int]
    # scores: list[float]
    # vectors: list[list[float]]  # 각 hit의 원본 벡터
    return ids, scores, vectors


engine = SearchEngine()
query = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

ids, scores = engine.search(query, top_k=10, search_fn=search_fn)
```

`search_fn` 계약:

- 시그니처: `search_fn(query, top_k)`
- 반환: `(ids, scores, vectors)`
- 제약:
  - 세 배열 길이는 동일해야 함
  - `vectors[i]` 차원은 쿼리 차원과 동일해야 함
  - `vectors`는 PRF 계산에 필수

## 디렉토리

```text
.
├── docs/arch/
├── docs/python/
├── docs/rust/
├── src/
│   ├── api/
│   ├── core/
│   ├── vdb/
│   └── math/
├── svve_core/
└── tests/
```

## 테스트

```bash
uv run pytest tests/python
cargo test --test rust_tests
```

## CI / 배포

- 워크플로우: `.github/workflows/ci.yml`
- `main` 브랜치 push/merge 시에만 실행
  - Linux에서 `cargo check --all-targets`
  - Linux에서 `uv run pytest tests/python`
  - Linux/macOS/Windows wheel 빌드
  - sdist 빌드
- CI 성공 후 자동 버저닝 수행
  - `BREAKING CHANGE` 또는 `type!:` 커밋 포함: `major`
  - `feat:` 커밋 포함: `minor`
  - 그 외: `patch`
  - `pyproject.toml`과 `Cargo.toml` 버전을 동기 갱신
  - `chore(release): vX.Y.Z [skip ci]` 커밋 + `vX.Y.Z` 태그 자동 생성

## 문서

- `docs/arch/blueprint.md`
- `docs/arch/theoretical_background.md`
- `docs/arch/how-this-works.md`
- `docs/python/README.md`
- `docs/python/module_reference.md`
- `docs/rust/README.md`
- `docs/rust/module_reference.md`
