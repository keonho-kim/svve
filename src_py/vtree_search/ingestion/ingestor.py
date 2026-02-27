"""
목적:
- 문서 적재용 공개 클래스 `VtreeIngestor`를 제공한다.

설명:
- summary/page 노드 upsert와 summary 갱신 트리거를 Rust 적재 브릿지에 위임한다.
- 파일 기반 전처리(표/이미지 주석 포함)를 통해 page 노드를 생성하는 기능을 제공한다.

디자인 패턴:
- 서비스 레이어(Service Layer).

참조:
- src_py/vtree_search/runtime/bridge.py
- src_py/vtree_search/contracts/ingestion_models.py
- src_py/vtree_search/ingestion/source_parser.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from vtree_search.config.models import IngestionConfig
from vtree_search.contracts.ingestion_models import (
    IngestionDocument,
    IngestionPageNode,
    IngestionResult,
    IngestionSummaryNode,
)
from vtree_search.ingestion.source_parser import build_source_parser
from vtree_search.llm.langchain_ingestion import LangChainIngestionAnnotationLLM
from vtree_search.runtime.bridge import RustRuntimeBridge


class VtreeIngestor:
    """문서 적재용 엔진 클래스."""

    def __init__(
        self,
        config: IngestionConfig,
        llm=None,
        runtime_bridge: RustRuntimeBridge | None = None,
    ) -> None:
        self._config = config
        self._annotation_llm = (
            None if llm is None else LangChainIngestionAnnotationLLM(chat_model=llm)
        )
        self._runtime_bridge = runtime_bridge or RustRuntimeBridge()

    async def upsert_document(self, document: IngestionDocument) -> IngestionResult:
        """문서 단위 summary/page 노드를 upsert한다."""
        payload = self._build_ingestion_payload(
            operation="upsert_document",
            document_id=document.document_id,
            summary_nodes=[node.model_dump() for node in document.summary_nodes],
            page_nodes=[node.model_dump() for node in document.page_nodes],
        )

        response = await asyncio.to_thread(self._runtime_bridge.execute_ingestion_job, payload)
        return IngestionResult.model_validate(response)

    async def upsert_pages(self, document_id: str, pages: list[IngestionPageNode]) -> IngestionResult:
        """페이지 노드만 upsert한다."""
        payload = self._build_ingestion_payload(
            operation="upsert_pages",
            document_id=document_id,
            summary_nodes=[],
            page_nodes=[node.model_dump() for node in pages],
        )

        response = await asyncio.to_thread(self._runtime_bridge.execute_ingestion_job, payload)
        return IngestionResult.model_validate(response)

    async def rebuild_summary_embeddings(self, document_id: str) -> IngestionResult:
        """summary 노드 갱신 트리거를 실행한다."""
        payload = self._build_ingestion_payload(
            operation="rebuild_summary_embeddings",
            document_id=document_id,
            summary_nodes=[],
            page_nodes=[],
        )

        response = await asyncio.to_thread(self._runtime_bridge.execute_ingestion_job, payload)
        return IngestionResult.model_validate(response)

    async def build_page_nodes_from_path(
        self,
        *,
        document_id: str,
        parent_node_id: str,
        input_root: str | Path,
        sample: bool | None = None,
    ) -> list[IngestionPageNode]:
        """입력 파일 루트에서 페이지 노드를 생성한다.

        Args:
            document_id: 대상 문서 ID.
            parent_node_id: 생성할 페이지 노드의 부모(summary) 노드 ID.
            input_root: 파싱 대상 루트 경로.
            sample: True면 확장자별 1개 파일만 처리.

        Returns:
            적재 가능한 `IngestionPageNode` 목록.
        """
        parser = build_source_parser(self._config, annotation_llm=self._annotation_llm)
        return await parser.build_page_nodes_from_files(
            document_id=document_id,
            parent_node_id=parent_node_id,
            input_root=input_root,
            sample=sample,
        )

    async def upsert_document_from_path(
        self,
        *,
        document_id: str,
        summary_nodes: list[IngestionSummaryNode],
        parent_node_id: str,
        input_root: str | Path,
        sample: bool | None = None,
    ) -> IngestionResult:
        """입력 파일에서 page 노드를 생성해 문서 단위로 업서트한다."""
        page_nodes = await self.build_page_nodes_from_path(
            document_id=document_id,
            parent_node_id=parent_node_id,
            input_root=input_root,
            sample=sample,
        )

        document = IngestionDocument(
            document_id=document_id,
            summary_nodes=summary_nodes,
            page_nodes=page_nodes,
        )
        return await self.upsert_document(document)

    def _build_ingestion_payload(
        self,
        operation: str,
        document_id: str | None,
        summary_nodes: list[dict[str, Any]],
        page_nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "operation": operation,
            "document_id": document_id,
            "summary_nodes": summary_nodes,
            "page_nodes": page_nodes,
            "postgres": {
                "dsn": self._config.postgres.to_dsn(),
                "summary_table": self._config.postgres.summary_table,
                "page_table": self._config.postgres.page_table,
                "pool_min": self._config.postgres.pool_min,
                "pool_max": self._config.postgres.pool_max,
                "connect_timeout_ms": self._config.postgres.connect_timeout_ms,
                "statement_timeout_ms": self._config.postgres.statement_timeout_ms,
            },
        }
