# Python 모듈/함수 레퍼런스

## 1) `svve_core/__init__.py`

### 역할

- 라이브러리 외부로 노출할 심볼을 단일 지점에서 정의

### 노출 심볼

| 식별자 | 설명 |
|---|---|
| `SearchEngine` | 사용자 검색 API 엔트리 클래스 |
| `SVVEError` | 공통 베이스 예외 |
| `QueryValidationError` | 입력 검증 실패 예외 |
| `SearchExecutionError` | Rust 실행 실패 예외 |

`__all__`은 위 4개 심볼만 export한다.

## 2) `svve_core/exceptions.py`

### 역할

- 예외 계층 표준화

### 클래스

| 클래스 | 상속 | 사용 시점 |
|---|---|---|
| `SVVEError` | `Exception` | 라이브러리 공통 베이스 |
| `QueryValidationError` | `SVVEError` | 입력/요청 파라미터 검증 실패 |
| `SearchExecutionError` | `SVVEError` | Rust 코어 실행 중 실패 |

## 3) `svve_core/schemas.py`

### 역할

- 사용자 입력을 Rust가 기대하는 형식으로 강제

### 모델

| 식별자 | 종류 | 필드/동작 |
|---|---|---|
| `SearchRequest` | `pydantic.BaseModel` | `query: np.ndarray`, `top_k: int(>=1)` |

### 함수(validator)

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `validate_query` | `@field_validator("query", mode="before")` | 입력을 contiguous `np.float32` 1D 배열로 변환 | 1D가 아니면 `ValueError("query must be a 1D numpy array")` |

## 4) `svve_core/engine.py`

### 역할

- 사용자 API 구현
- Python 검증/예외를 Rust 경계와 연결

### 타입 별칭

| 식별자 | 정의 | 의미 |
|---|---|---|
| `SearchFn` | `Callable[[NDArray[np.float32], int], tuple[list[int], list[float], list[list[float]]]]` | 외부 VDB 검색 함수 인터페이스 |

### 클래스/메서드

| 식별자 | 시그니처 | 설명 | 실패 조건 |
|---|---|---|---|
| `SearchEngine.__init__` | `def __init__(self) -> None` | Rust 확장 객체(`_svve_core.SearchEngine`) 초기화 | 확장 모듈 import 실패 |
| `SearchEngine.search` | `def search(self, query: ArrayLike, top_k: int = 10, search_fn: SearchFn | None = None) -> tuple[NDArray[np.uint32], NDArray[np.float32]]` | 입력 검증 후 Rust 검색 호출, 결과 dtype 강제 | `search_fn is None`, Pydantic 검증 실패, Rust `RuntimeError` |

### `search_fn` 인터페이스 규칙

| 항목 | 규칙 |
|---|---|
| 시그니처 | `search_fn(query, top_k)` |
| 반환 형식 | `(ids, scores, vectors)` |
| 길이 제약 | `len(ids) == len(scores) == len(vectors)` |
| 차원 제약 | 각 `vectors[i]` 차원은 쿼리 차원과 동일 |
| 필수성 | PRF 계산을 위해 `vectors`는 반드시 필요 |

실제 상세 검증은 Rust `CallbackVdb`에서 수행된다.

## 5) 테스트 매핑

### `tests/python/test_schemas.py`

| 테스트명 | 검증 내용 |
|---|---|
| `test_search_request_normalizes_query_dtype_and_shape` | dtype(`float32`), 1D, contiguous 정규화 확인 |
| `test_search_request_rejects_non_1d_query` | 2D 입력 거부 확인 |

## 6) 변경 영향도 빠른 가이드

- `SearchFn` 반환 형식 변경: Rust `src/vdb/adapter.rs`와 동시 수정 필요.
- `SearchRequest` validator 변경: Python 테스트와 Rust 입력 전제(1D float32 contiguous)에 영향.
- 예외 타입 변경: 사용자 애플리케이션의 예외 처리 코드 호환성 영향.
