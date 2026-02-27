"""
목적:
- 검색 엔진 계층의 공개 진입점을 제공한다.

설명:
- 큐잉 기반 검색 엔진 클래스를 외부에 노출한다.

디자인 패턴:
- 모듈 퍼사드(Module Facade).

참조:
- src_py/vtree_search/search/engine.py
"""

from .engine import VTreeSearchEngine

__all__ = ["VTreeSearchEngine"]
