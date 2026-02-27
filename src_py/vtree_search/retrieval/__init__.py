"""
목적:
- 검색 계층의 공개 심볼을 정의한다.

설명:
- 외부에는 `VTreeSearchEngine`을 기본 진입점으로 제공한다.

디자인 패턴:
- 모듈 퍼사드(Module Facade).

참조:
- src_py/vtree_search/search/engine.py
"""

from vtree_search.search.engine import VTreeSearchEngine

__all__ = ["VTreeSearchEngine"]
