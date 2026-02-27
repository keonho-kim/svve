# Python 테스트 안내

## 목적
- `src_py/vtree_search` 라이브러리 계층 통합 테스트 위치를 정의한다.

## 권장 범위
- Redis Streams 실연동
- Postgres(`pgvector`, `ltree`) 실연동
- 잡 상태 전이(PENDING/RUNNING/SUCCEEDED/FAILED/CANCELED)
- 재시도 및 DLQ 경로

## 실행 핸드오프
- `uv run pytest tests/python -m integration`
