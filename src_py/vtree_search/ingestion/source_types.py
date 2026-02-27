"""
목적:
- 파일 파싱 단계의 중간 블록 타입을 정의한다.

설명:
- 문서 파싱 결과(텍스트/표/이미지)를 단일 모델로 통일해
  청킹/노드 생성 단계에서 재사용한다.

디자인 패턴:
- 데이터 클래스(Data Class).

참조:
- src_py/vtree_search/ingestion/source_parser.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedBlock:
    """문서에서 추출한 단일 블록 모델."""

    source_file: str
    page_num: int
    block_type: str
    text: str
    metadata: dict[str, object]
