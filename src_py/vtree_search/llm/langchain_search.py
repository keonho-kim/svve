"""
목적:
- LangChain `ainvoke` 기반 검색 필터 어댑터를 제공한다.

설명:
- 질문/후보 목록을 LLM에 전달해 후보별 keep/drop 판정을 JSON으로 받는다.
- 응답 형식 위반(잘못된 JSON/누락 node_id)은 즉시 오류로 처리한다.

디자인 패턴:
- 어댑터(Adapter).

참조:
- src_py/vtree_search/llm/contracts.py
- src_py/vtree_search/search/engine.py
"""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate

from vtree_search.exceptions import ConfigurationError
from vtree_search.llm.contracts import (
    SearchFilterCandidate,
    SearchFilterDecision,
)


class LangChainSearchFilterLLM:
    """LangChain 채팅 모델을 검색 필터로 감싸는 어댑터."""

    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "당신은 검색 후보 필터다. 반드시 JSON 배열만 반환한다. "
                        "각 항목 형식은 {\"node_id\": str, \"keep\": bool, \"reason\": str} 이다."
                    ),
                ),
                (
                    "human",
                    (
                        "질문:\n{question}\n\n"
                        "후보(JSON):\n{candidates_json}\n\n"
                        "모든 후보를 빠짐없이 1개씩 판단해 JSON 배열만 출력하라."
                    ),
                ),
            ]
        )

    async def filter(
        self,
        *,
        question: str,
        candidates: list[SearchFilterCandidate],
    ) -> list[SearchFilterDecision]:
        candidates_json = json.dumps(
            [candidate.model_dump() for candidate in candidates],
            ensure_ascii=False,
        )
        prompt_value = self._prompt.invoke(
            {
                "question": question,
                "candidates_json": candidates_json,
            }
        )
        response = await self._chat_model.ainvoke(prompt_value)
        response_text = _read_message_text(response)

        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"검색 필터 LLM 응답 JSON 파싱 실패: {exc}") from exc

        if not isinstance(raw, list):
            raise ConfigurationError("검색 필터 LLM 응답은 JSON 배열이어야 합니다")

        decisions = [SearchFilterDecision.model_validate(item) for item in raw]
        _validate_decisions(candidates=candidates, decisions=decisions)
        return decisions


def _read_message_text(message) -> str:
    content = getattr(message, "content", None)
    if not isinstance(content, str):
        raise ConfigurationError("검색 필터 LLM 응답 content는 문자열이어야 합니다")

    text = content.strip()
    if not text:
        raise ConfigurationError("검색 필터 LLM 응답이 비어 있습니다")
    return text


def _validate_decisions(
    *,
    candidates: list[SearchFilterCandidate],
    decisions: list[SearchFilterDecision],
) -> None:
    expected_ids = {candidate.node_id for candidate in candidates}
    seen_ids: set[str] = set()

    for decision in decisions:
        if decision.node_id not in expected_ids:
            raise ConfigurationError(
                f"검색 필터 LLM 응답 node_id가 후보 집합에 없습니다: {decision.node_id}"
            )
        if decision.node_id in seen_ids:
            raise ConfigurationError(
                f"검색 필터 LLM 응답 node_id가 중복되었습니다: {decision.node_id}"
            )
        seen_ids.add(decision.node_id)

    missing_ids = expected_ids - seen_ids
    if missing_ids:
        missing_joined = ", ".join(sorted(missing_ids))
        raise ConfigurationError(f"검색 필터 LLM 응답 누락 node_id: {missing_joined}")
