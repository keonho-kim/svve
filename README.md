# Vtree Search

Vtree Search는 **Python 라이브러리** 형태의 멀티모달 계층형 RAG 엔진입니다.

핵심 실행 구조는 아래와 같습니다.

1. Rust에서 검색/적재 로직 실행
2. Python이 FFI 브릿지 래핑
3. Python 클래스 두 개(`VtreeIngestor`, `VTreeSearchEngine`)를 외부에 제공
4. 애플리케이션(BE)이 HTTP/API/인증/멀티테넌시를 담당

## 현재 제공 클래스

- `VtreeIngestor`: summary/page 노드 upsert, summary 갱신 트리거
- `VTreeSearchEngine`: Redis Streams 큐 제출/워커 처리/상태 조회/결과 조회/취소

## Ingestion 멀티모달 처리

- `source_parser`가 Markdown/PDF/DOCX를 파싱한다.
- PDF 표/이미지, DOCX 표를 주석 서비스와 연동해 구조화 본문(`[TBL]`, `[IMG]`)으로 변환한다.
- DOCX는 레이아웃 추정 유틸을 통해 페이지 번호/문단 메타데이터를 보강한다.

## 부하 제어 기본값

- 큐 모델: Redis Streams + Consumer Group
- 큐 보장: At-least-once
- 큐 임계치: `QUEUE_MAX_LEN=200`, `QUEUE_REJECT_AT=180`
- 재시도: `max_retries=3`, 지수 백오프(`200ms`~`2s`), 초과 시 DLQ
- 큐 포화 시 즉시 거절: 라이브러리 예외 `QueueOverloadedError`

## `.env` 정책

- 라이브러리 본체는 `.env`를 읽지 않는다.
- 루트 `.env`는 드라이버 코드(`scripts/run-search.py`)에서만 읽는다.
- 샘플 키는 `.env.example` 참고.

## 디렉토리

```text
.
├── src_py/vtree_search/
│   ├── config/
│   ├── contracts/
│   ├── ingestion/
│   ├── queue/
│   ├── runtime/
│   └── search/
├── src_rs/
│   ├── api/
│   ├── core/
│   ├── index/
│   └── math/
├── docs/
│   ├── arch/
│   ├── python/
│   ├── rust/
│   └── ops/
└── scripts/
```

## 문서 인덱스

- 아키텍처 청사진: `docs/arch/blueprint.md`
- 런타임 흐름: `docs/arch/how-this-works.md`
- 이론 배경: `docs/arch/theoretical_background.md`
- 운영/SLO/큐잉: `docs/ops/queueing-and-slo.md`
- Python 모듈 문서: `docs/python/README.md`, `docs/python/module_reference.md`
- Rust 모듈 문서: `docs/rust/README.md`, `docs/rust/module_reference.md`

## 드라이버 실행 예시

```bash
uv run python scripts/run-search.py \
  --query "문서에서 환불 정책을 찾아줘" \
  --embedding "0.1,0.2,0.3,0.4" \
  --top-k 5
```

## 테스트 명령 핸드오프

- Python: `uv run pytest tests/python -m integration`
- Rust: `cargo test --test rust_tests`

주의: 본 작업에서는 테스트를 실행하지 않고 코드/문서만 제공합니다.
