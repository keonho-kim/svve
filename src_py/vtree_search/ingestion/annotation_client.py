"""
목적:
- 표/이미지 주석 생성을 위한 HTTP 클라이언트를 제공한다.

설명:
- 외부 주석 서비스와 통신해 [TBL]/[IMG] 본문을 생성한다.
- 응답 본문은 텍스트 계약을 기준으로 처리한다.

디자인 패턴:
- 어댑터(Adapter).

참조:
- src_py/vtree_search/config/models.py
- src_py/vtree_search/ingestion/source_parser.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from vtree_search.config.models import IngestionAnnotationConfig
from vtree_search.exceptions import IngestionProcessingError


class IngestionAnnotationClient:
    """적재 주석 HTTP 클라이언트."""

    def __init__(self, config: IngestionAnnotationConfig) -> None:
        self._config = config
        self._client = httpx.Client(timeout=config.timeout_ms / 1000.0)

    def annotate_table(self, *, table_html: str, page_text: str) -> str:
        """표 HTML에 대한 주석 본문을 생성한다."""
        payload = {
            "kind": "table",
            "table_html": table_html,
            "page_text": page_text,
            "model": self._config.model,
        }
        parsed = self._request(payload)
        if parsed.startswith("[TBL]"):
            return parsed
        return _to_table_block(table_html=table_html, text=parsed)

    def annotate_image(self, *, image_path: Path, page_text: str) -> str:
        """이미지 파일에 대한 주석 본문을 생성한다."""
        payload = {
            "kind": "image",
            "image_path": image_path.as_posix(),
            "page_text": page_text,
            "model": self._config.model,
        }
        parsed = self._request(payload)
        if parsed.startswith("[IMG]"):
            return parsed
        return _to_image_block(image_path=image_path, text=parsed)

    def _request(self, payload: dict[str, Any]) -> str:
        headers = {"Content-Type": "application/json"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        try:
            response = self._client.post(self._config.url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise IngestionProcessingError(f"주석 HTTP 호출 실패: {exc}") from exc

        text_body = response.text.strip()
        if not text_body:
            raise IngestionProcessingError("주석 서비스 응답 본문이 비어 있습니다")
        return text_body


def _to_table_block(*, table_html: str, text: str) -> str:
    normalized = " ".join(text.split())
    normalized_html = table_html.strip() or "<table><tbody><tr><td></td></tr></tbody></table>"
    return (
        "[TBL]\n"
        f"<HTML>{normalized_html}</HTML>\n"
        f"<SUMMARY>{normalized}</SUMMARY>\n"
        f"<DESCRIPTION>{normalized}</DESCRIPTION>\n"
        "[/TBL]"
    )


def _to_image_block(*, image_path: Path, text: str) -> str:
    normalized = " ".join(text.split())
    return (
        "[IMG]\n"
        f"<PATH>{image_path.as_posix()}</PATH>\n"
        f"<SUMMARY>{normalized}</SUMMARY>\n"
        f"<DESCRIPTION>{normalized}</DESCRIPTION>\n"
        "[/IMG]"
    )
