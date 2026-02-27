"""
목적:
- LangChain `ainvoke` 기반 적재 주석 어댑터를 제공한다.

설명:
- 표/이미지 입력을 프롬프트에 주입해 `[TBL]`/`[IMG]` 블록을 생성한다.
- 응답 형식이 정의와 다르면 즉시 실패한다.

디자인 패턴:
- 어댑터(Adapter).

참조:
- src_py/vtree_search/llm/contracts.py
- src_py/vtree_search/ingestion/prompts/table_prompt.py
- src_py/vtree_search/ingestion/prompts/image_prompt.py
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from vtree_search.exceptions import IngestionProcessingError
from vtree_search.ingestion.prompts import IMAGE_PROMPT, TABLE_PROMPT


class LangChainIngestionAnnotationLLM:
    """LangChain 채팅 모델을 적재 주석기로 감싸는 어댑터."""

    def __init__(self, chat_model) -> None:
        self._chat_model = chat_model
        self._table_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TABLE_PROMPT),
                (
                    "human",
                    (
                        "page_text:\n{page_text}\n\n"
                        "table_html:\n{table_html}\n\n"
                        "형식 규칙을 지켜 출력하라."
                    ),
                ),
            ]
        )
        self._image_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", IMAGE_PROMPT),
                (
                    "human",
                    (
                        "page_text:\n{page_text}\n\n"
                        "image_path:\n{image_path}\n\n"
                        "형식 규칙을 지켜 출력하라."
                    ),
                ),
            ]
        )

    async def annotate_table(self, *, table_html: str, page_text: str) -> str:
        prompt_value = self._table_prompt.invoke(
            {
                "table_html": table_html,
                "page_text": page_text,
            }
        )
        response = await self._chat_model.ainvoke(prompt_value)
        text = _read_message_text(response)
        if not text.startswith("[TBL]") or not text.endswith("[/TBL]"):
            raise IngestionProcessingError("표 주석 LLM 응답 형식이 [TBL] 블록이 아닙니다")
        return text

    async def annotate_image(self, *, image_path: Path, page_text: str) -> str:
        prompt_value = self._image_prompt.invoke(
            {
                "image_path": image_path.as_posix(),
                "page_text": page_text,
            }
        )
        response = await self._chat_model.ainvoke(prompt_value)
        text = _read_message_text(response)
        if not text.startswith("[IMG]") or not text.endswith("[/IMG]"):
            raise IngestionProcessingError("이미지 주석 LLM 응답 형식이 [IMG] 블록이 아닙니다")
        return text


def _read_message_text(message) -> str:
    content = getattr(message, "content", None)
    if not isinstance(content, str):
        raise IngestionProcessingError("적재 주석 LLM 응답 content는 문자열이어야 합니다")

    text = content.strip()
    if not text:
        raise IngestionProcessingError("적재 주석 LLM 응답이 비어 있습니다")
    return text
