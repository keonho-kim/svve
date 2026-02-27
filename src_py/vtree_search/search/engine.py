"""
목적:
- Redis 큐잉 기반 검색 엔진 클래스를 제공한다.

설명:
- 검색 요청을 큐에 적재하고 잡 상태/결과를 조회한다.
- 워커에서 Rust 검색 브릿지를 호출해 실제 파이프라인을 실행한다.

디자인 패턴:
- 서비스 레이어(Service Layer) + 큐 소비자(Worker).

참조:
- src_py/vtree_search/runtime/bridge.py
- src_py/vtree_search/queue/redis_streams.py
- src_py/vtree_search/contracts/job_models.py
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from vtree_search.config.models import SearchConfig
from vtree_search.contracts.job_models import (
    SearchJobAccepted,
    SearchJobCanceled,
    SearchJobResult,
    SearchJobStatus,
)
from vtree_search.contracts.search_models import SearchSubmission
from vtree_search.exceptions import (
    ConfigurationError,
    JobExpiredError,
    JobFailedError,
    JobNotFoundError,
)
from vtree_search.queue.redis_streams import QueueMessage, RedisSearchQueue
from vtree_search.runtime.bridge import RustRuntimeBridge


class VTreeSearchEngine:
    """Redis 큐를 사용하는 검색 엔진 클래스."""

    def __init__(
        self,
        config: SearchConfig,
        runtime_bridge: RustRuntimeBridge | None = None,
        queue: RedisSearchQueue | None = None,
    ) -> None:
        self._config = config
        self._runtime_bridge = runtime_bridge or RustRuntimeBridge()
        self._queue = queue or RedisSearchQueue(config.redis)
        self._queue.ensure_consumer_group()

    def submit_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        metadata: dict[str, object] | None = None,
    ) -> SearchJobAccepted:
        """검색 작업을 큐에 제출한다."""
        if top_k < 1:
            raise ConfigurationError("top_k는 1 이상이어야 합니다")

        if len(query_embedding) != self._config.postgres.embedding_dim:
            raise ConfigurationError(
                "query_embedding 길이가 embedding_dim과 일치하지 않습니다: "
                f"expected={self._config.postgres.embedding_dim}, actual={len(query_embedding)}"
            )

        self._queue.guard_capacity()

        job_id = uuid4().hex
        submission = SearchSubmission(
            job_id=job_id,
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=top_k,
            metadata=metadata,
        )

        payload = self._build_rust_payload(submission)
        payload_json = json.dumps(payload, ensure_ascii=False)

        self._queue.create_job_record(job_id, payload_json)
        self._queue.enqueue(job_id=job_id, payload_json=payload_json, retries=0)

        return SearchJobAccepted(
            job_id=job_id,
            state="PENDING",
            submitted_at=_utc_now(),
        )

    def get_job(self, job_id: str) -> SearchJobStatus:
        """잡 상태를 조회한다."""
        record = self._queue.get_job_record(job_id)
        if record is None:
            raise JobNotFoundError(f"job_id={job_id}를 찾을 수 없습니다")

        return SearchJobStatus(
            job_id=job_id,
            state=str(record.get("state", "PENDING")),
            retries=int(record.get("retries", "0") or "0"),
            canceled=record.get("canceled", "0") == "1",
            updated_at=str(record.get("updated_at", _utc_now())),
            last_error=record.get("last_error") or None,
        )

    def fetch_result(self, job_id: str) -> SearchJobResult:
        """성공한 잡의 결과를 조회한다."""
        record = self._queue.get_job_record(job_id)
        if record is None:
            raise JobExpiredError(f"job_id={job_id} 결과가 만료되었거나 존재하지 않습니다")

        state = str(record.get("state", "PENDING"))
        if state == "FAILED":
            raise JobFailedError(record.get("last_error") or f"job_id={job_id}가 실패했습니다")
        if state != "SUCCEEDED":
            raise JobFailedError(f"job_id={job_id} 상태가 SUCCEEDED가 아닙니다: {state}")

        result_json = record.get("result_json") or ""
        if not result_json:
            raise JobFailedError(f"job_id={job_id}의 result_json이 비어 있습니다")

        try:
            payload = json.loads(result_json)
        except json.JSONDecodeError as exc:
            raise JobFailedError(f"job_id={job_id} 결과 JSON 파싱 실패: {exc}") from exc

        payload["state"] = "SUCCEEDED"
        payload["completed_at"] = record.get("completed_at") or record.get("updated_at") or _utc_now()
        return SearchJobResult.model_validate(payload)

    def cancel_job(self, job_id: str) -> SearchJobCanceled:
        """잡 취소를 요청한다."""
        record = self._queue.get_job_record(job_id)
        if record is None:
            raise JobNotFoundError(f"job_id={job_id}를 찾을 수 없습니다")

        state = str(record.get("state", "PENDING"))
        if state in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return SearchJobCanceled(
                job_id=job_id,
                state="CANCELED" if state == "CANCELED" else "CANCELED",
                message=f"이미 종결된 작업입니다: current_state={state}",
            )

        self._queue.mark_cancel_requested(job_id)
        if state == "PENDING":
            self._queue.mark_canceled(job_id)

        return SearchJobCanceled(
            job_id=job_id,
            state="CANCELED",
            message="취소 요청이 접수되었습니다",
        )

    def run_worker_once(self, worker_name: str, max_items: int = 1) -> int:
        """큐에서 최대 max_items개 작업을 처리한다."""
        if max_items < 1:
            raise ConfigurationError("max_items는 1 이상이어야 합니다")

        messages = self._queue.read(consumer_name=worker_name, count=max_items)
        processed = 0

        for message in messages:
            self._process_message(message)
            processed += 1

        return processed

    def run_worker_forever(self, worker_name: str) -> None:
        """큐 작업을 지속적으로 처리한다."""
        while True:
            processed = self.run_worker_once(worker_name=worker_name, max_items=1)
            if processed == 0:
                time.sleep(0.05)

    def _process_message(self, message: QueueMessage) -> None:
        job_id = message.fields.get("job_id", "")
        if not job_id:
            self._queue.ack(message)
            return

        record = self._queue.get_job_record(job_id)
        if record is None:
            self._queue.ack(message)
            return

        if record.get("canceled", "0") == "1":
            self._queue.mark_canceled(job_id)
            self._queue.ack(message)
            return

        retries = int(message.fields.get("retries", record.get("retries", "0") or "0") or "0")
        self._queue.mark_running(job_id, retries)

        payload_json = message.fields.get("payload_json") or record.get("payload_json") or ""
        if not payload_json:
            self._queue.mark_failed(job_id, "payload_json이 비어 있습니다", retries)
            self._queue.move_to_dlq(message, "payload_json-empty")
            self._queue.ack(message)
            return

        try:
            payload = json.loads(payload_json)
            result = self._runtime_bridge.execute_search_job(payload)
        except Exception as exc:  # noqa: BLE001
            next_retry = retries + 1
            error_message = str(exc)

            if next_retry <= self._config.max_retries:
                backoff_ms = min(
                    self._config.retry_base_ms * (2 ** max(0, next_retry - 1)),
                    self._config.retry_max_ms,
                )
                self._queue.mark_pending_retry(job_id, next_retry, error_message)
                self._queue.enqueue(job_id=job_id, payload_json=payload_json, retries=next_retry)
                time.sleep(backoff_ms / 1000.0)
            else:
                self._queue.mark_failed(job_id, error_message, next_retry)
                self._queue.move_to_dlq(message, error_message)

            self._queue.ack(message)
            return

        self._queue.mark_succeeded(job_id, result)
        self._queue.ack(message)

    def _build_rust_payload(self, submission: SearchSubmission) -> dict[str, Any]:
        return {
            "job_id": submission.job_id,
            "question": submission.query_text,
            "query_embedding": submission.query_embedding,
            "top_k": submission.top_k,
            "entry_limit": self._config.entry_limit,
            "page_limit": self._config.page_limit,
            "worker_concurrency": self._config.worker_concurrency,
            "postgres": {
                "dsn": self._config.postgres.dsn,
                "summary_table": self._config.postgres.summary_table,
                "page_table": self._config.postgres.page_table,
                "pool_min": self._config.postgres.pool_min,
                "pool_max": self._config.postgres.pool_max,
                "connect_timeout_ms": self._config.postgres.connect_timeout_ms,
                "statement_timeout_ms": self._config.postgres.statement_timeout_ms,
            },
            "filter_http": {
                "url": self._config.filter_http.url,
                "timeout_ms": self._config.filter_http.timeout_ms,
                "auth_token": self._config.filter_http.auth_token,
                "model": self._config.filter_http.model,
            },
            "metadata": submission.metadata,
        }


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()
