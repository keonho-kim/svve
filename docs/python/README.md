# Python 문서 개요

## 목적

이 문서는 `svve_core/` Python 계층의 역할과 유지보수 기준을 정리한 인덱스 문서다.  
핵심 관점은 "사용자 API 경계에서 어떤 검증/예외/호출을 담당하는가"이다.

## 현재 활성 컴포넌트

```text
svve_core/
├── __init__.py
├── engine.py
├── schemas.py
└── exceptions.py
```

## 호출 흐름

1. 사용자가 `svve_core.SearchEngine`를 생성한다.
2. `SearchEngine.search(query, top_k, search_fn)`가 입력을 `SearchRequest`로 검증한다.
3. 검증된 값과 `search_fn`을 Rust 확장 모듈(`_svve_core.SearchEngine.search`)에 전달한다.
4. Rust 결과를 `np.uint32` IDs, `np.float32` scores로 변환해 반환한다.
5. 입력 오류는 `QueryValidationError`, 실행 오류는 `SearchExecutionError`로 변환한다.

## 문서 목록

- `docs/python/module_reference.md`: 모듈별/함수별 상세 레퍼런스

## 유지보수 체크리스트

- 공개 API(`SearchEngine.search`) 시그니처 변경 시 `README.md` 사용 예시와 함께 갱신한다.
- 예외 타입/에러 메시지 정책 변경 시 `exceptions.py`와 본 문서를 함께 수정한다.
- 입력 검증 규칙(`schemas.py`) 변경 시 `tests/python/test_schemas.py` 케이스를 동기화한다.
