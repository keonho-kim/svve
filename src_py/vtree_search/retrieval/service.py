"""
목적:
- 검색 계층의 이전 경로 호환 진입점을 유지한다.

설명:
- `RetrievalService` 명칭은 `VTreeSearchEngine`으로 통합되었고,
  이 파일은 명시적 별칭만 제공한다.

디자인 패턴:
- 호환 어댑터(Compatibility Adapter).

참조:
- src_py/vtree_search/search/engine.py
"""

from vtree_search.search.engine import VTreeSearchEngine as RetrievalService

__all__ = ["RetrievalService"]
