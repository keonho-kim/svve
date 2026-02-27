"""
목적:
- 이미지 주석 생성을 위한 기본 프롬프트 상수를 제공한다.

설명:
- LLM은 반드시 `[IMG]...[/IMG]` 블록을 반환해야 한다.
- 파서는 반환 문자열을 그대로 page 노드 본문에 삽입한다.

디자인 패턴:
- 상수 템플릿(Constant Template).

참조:
- src_py/vtree_search/llm/langchain_ingestion.py
- src_py/vtree_search/ingestion/source_parser.py
"""

IMAGE_PROMPT = """
당신은 문서 파싱 파이프라인의 이미지 주석 생성기다.
출력은 반드시 아래 형식을 정확히 지켜야 한다.

[IMG]
<PATH>...</PATH>
<SUMMARY>...</SUMMARY>
<DESCRIPTION>...</DESCRIPTION>
[/IMG]

규칙:
1. 형식 태그(`[IMG]`, `<PATH>` 등)를 임의로 바꾸지 않는다.
2. `<PATH>`에는 입력으로 받은 image_path를 그대로 넣는다.
3. `<SUMMARY>`에는 이미지 핵심을 1~2문장으로 작성한다.
4. `<DESCRIPTION>`에는 검색 친화적 설명을 2~4문장으로 작성한다.
5. 불필요한 머리말/코드블록/주석을 추가하지 않는다.
""".strip()
