# Python 계층 개요 (Phase 2)

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
- `ingestion/`: 적재 서비스
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
- `ingestion/annotation_client.py`
  - 외부 주석 HTTP 서비스 연동
  - `[TBL]`/`[IMG]` 본문 포맷 표준화

## `example-ingestion-python` 통합 매핑

- `example-ingestion-python/core/docx_layout.py`
  - `vtree_search/ingestion/docx_layout.py`로 이식
- `example-ingestion-python/core/file_parser.py`의 표/이미지 흐름
  - `vtree_search/ingestion/source_parser.py`로 통합
- `example-ingestion-python/core/table_annotation.py`, `image_annotation.py`
  - 외부 HTTP 연동형 `vtree_search/ingestion/annotation_client.py`로 대체

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

### 소비자 앱 책임

- HTTP API 구현
- 인증/인가
- 멀티테넌시
- 요청 라우팅

## `.env` 원칙

- 라이브러리 내부에서 `.env`를 읽지 않는다.
- `scripts/run-search.py` 같은 드라이버 코드에서 `.env`를 읽어 설정을 주입한다.
