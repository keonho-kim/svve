"""
목적:
- Python과 Rust 확장 모듈 간 호출 경계를 제공한다.

설명:
- JSON payload를 Rust 브릿지에 전달하고 결과 JSON을 dict로 변환한다.
- Rust 모듈 미설치/호출 실패를 명시적 예외로 변환한다.

디자인 패턴:
- 어댑터(Adapter).

참조:
- src_rs/api/search_bridge.rs
- src_rs/api/ingestion_bridge.rs
"""

from __future__ import annotations

import json
from typing import Any

from vtree_search.exceptions import DependencyUnavailableError, JobFailedError


class RustRuntimeBridge:
    """Rust FFI 브릿지 래퍼."""

    def __init__(self) -> None:
        try:
            from vtree_search import _vtree_search  # type: ignore
        except Exception as exc:  # pragma: no cover - 런타임 환경 의존
            raise DependencyUnavailableError(
                f"Rust 확장 모듈(_vtree_search)을 불러오지 못했습니다: {exc}"
            ) from exc

        self._search = _vtree_search.SearchBridge()
        self._ingestion = _vtree_search.IngestionBridge()

    def execute_search_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        """검색 작업을 Rust 브릿지로 실행한다."""
        return self._execute(self._search.execute, payload)

    def execute_ingestion_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        """적재 작업을 Rust 브릿지로 실행한다."""
        return self._execute(self._ingestion.execute, payload)

    def search_status(self) -> str:
        """검색 브릿지 상태 문자열을 반환한다."""
        return str(self._search.status())

    def ingestion_status(self) -> str:
        """적재 브릿지 상태 문자열을 반환한다."""
        return str(self._ingestion.status())

    @staticmethod
    def _execute(callable_fn, payload: dict[str, Any]) -> dict[str, Any]:
        payload_json = json.dumps(payload, ensure_ascii=False)
        try:
            response_json = callable_fn(payload_json)
        except RuntimeError as exc:
            raise JobFailedError(f"Rust 브릿지 실행 실패: {exc}") from exc

        try:
            return json.loads(response_json)
        except json.JSONDecodeError as exc:
            raise JobFailedError(f"Rust 응답 JSON 파싱 실패: {exc}") from exc
