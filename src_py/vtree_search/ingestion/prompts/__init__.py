"""
목적:
- 적재 프롬프트 상수 공개 진입점을 제공한다.

설명:
- 표/이미지 주석 프롬프트를 별도 파일로 분리해 변경 범위를 최소화한다.

디자인 패턴:
- 모듈 퍼사드(Module Facade).

참조:
- src_py/vtree_search/ingestion/prompts/table_prompt.py
- src_py/vtree_search/ingestion/prompts/image_prompt.py
"""

from .image_prompt import IMAGE_PROMPT
from .table_prompt import TABLE_PROMPT

__all__ = ["TABLE_PROMPT", "IMAGE_PROMPT"]
