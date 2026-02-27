# Python 계층 개요 (Phase 3)

## 관련 문서

- [프로젝트 개요](../../README.md)
- [아키텍처 청사진](../arch/blueprint.md)
- [런타임 동작](../arch/how-this-works.md)
- [Python LLM 주입](./llm_injection.md)
- [Python 모듈 레퍼런스](./module_reference.md)
- [Rust 개요](../rust/README.md)
- [운영 가이드](../ops/queueing-and-slo.md)

## 목적

`src_py/vtree_search`의 공개 라이브러리 경계를 정의한다.

## 핵심 클래스

- `VtreeIngestor`
  - 적재 업서트/갱신 트리거
- `VTreeSearchEngine`
  - 잡 제출/워커 실행/상태 조회/결과 조회/취소

## 필수 모듈

- `config/`: 설정 모델
- `contracts/`: DTO/잡 상태 모델
- `runtime/`: Rust 브릿지 래퍼
- `queue/`: Redis Streams 제어
- `llm/`: LangChain 주입 DTO/어댑터
- `ingestion/`: 적재 서비스 + `prompts/`
- `search/`: 검색 서비스

## Ingestion 멀티모달 처리 모듈

- `ingestion/source_parser.py`
  - Markdown/PDF/DOCX 파싱
  - PDF 표/이미지 주석 본문 생성
  - page 노드 변환
- `ingestion/docx_layout.py`
  - DOCX 레이아웃 기반 페이지 추정(A4 기준)
  - 문단/표 높이 추정
- `ingestion/parser_helpers.py`
  - 표 HTML 직렬화
  - DOCX 제목 레벨 추정
  - PDF 이미지 bbox -> 픽셀 변환
  - 블록 청킹
- `ingestion/prompts/table_prompt.py`, `image_prompt.py`
  - `TABLE_PROMPT`, `IMAGE_PROMPT` 상수

## Ingestion 부하 제어 포인트

- `IngestionPreprocessConfig.sample_per_extension`
  - 샘플 ingest(확장자별 1개)로 비용 검증
- `IngestionPreprocessConfig.max_chunk_chars`
  - 문단 결합 최대 길이 제한
- `IngestionPreprocessConfig.enable_table_annotation`
  - 표 주석 호출 on/off
- `IngestionPreprocessConfig.enable_image_annotation`
  - 이미지 주석 호출 on/off
- `IngestionPreprocessConfig.asset_output_dir`
  - 추출 이미지 저장 경로 제어

## 책임 분리

### 라이브러리 책임

- Rust 실행 경로 연결
- 잡 큐잉/재시도/DLQ
- 명시적 예외 타입 제공
- LLM 호출 형식 강제

### 소비자 앱 책임

- HTTP API 구현
- 인증/인가
- 멀티테넌시
- 요청 라우팅
- 실제 모델 선택(OpenAI/Bedrock 등)

## `.env` 원칙

- 라이브러리 내부에서 `.env`를 읽지 않는다.
- `scripts/run-search.py`, `scripts/run-ingestion.py` 같은 드라이버 코드에서 `.env`를 읽어 설정을 주입한다.
- LLM 설정은 `.env` 대신 팩토리 함수(`--llm-factory`)로 주입한다.
