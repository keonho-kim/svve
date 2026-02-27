"""
목적:
- 검색 엔진 결과를 상위 애플리케이션 응답 형식으로 조정한다.

설명:
- 라이브러리 경계에서 최소 오케스트레이션 유틸을 제공한다.
- HTTP 응답 생성 책임은 소비자 애플리케이션이 가진다.

디자인 패턴:
- 조정자(Coordinator).

참조:
- src_py/vtree_search/search/engine.py
"""

from __future__ import annotations

from vtree_search.contracts.job_models import SearchJobResult
from vtree_search.search.engine import VTreeSearchEngine


class QueryCoordinator:
    """검색 엔진 응답 조정용 유틸 클래스."""

    def __init__(self, search_engine: VTreeSearchEngine) -> None:
        self._search_engine = search_engine

    def fetch_ready_result(self, job_id: str) -> dict[str, object]:
        """완료된 잡 결과를 사전(dict) 형태로 반환한다."""
        result: SearchJobResult = self._search_engine.fetch_result(job_id)
        return result.model_dump()
