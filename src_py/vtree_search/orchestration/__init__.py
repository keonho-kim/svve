"""
목적:
- 질의 오케스트레이션 계층의 공개 심볼을 정의한다.

설명:
- 메인 LLM 조립 단계의 경계 클래스를 외부에 노출한다.

디자인 패턴:
- 퍼사드(Facade).

참조:
- src_py/vtree_search/orchestration/coordinator.py
"""

from .coordinator import QueryCoordinator

__all__ = ["QueryCoordinator"]
