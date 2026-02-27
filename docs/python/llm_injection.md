# Python LLM 주입 가이드

## 관련 문서

- [프로젝트 개요](../../README.md)
- [Python 개요](./README.md)
- [Python 모듈 레퍼런스](./module_reference.md)
- [아키텍처 청사진](../arch/blueprint.md)

## 1. 목표

Vtree Search는 LLM 연동을 HTTP가 아닌 **Python 인자 주입 방식**으로 처리한다.

- 검색: 후보 keep/drop 판정
- 적재: 표/이미지 주석 생성

## 2. 직접 주입 방식

애플리케이션은 LangChain 채팅 모델 구현체를 직접 생성해 주입한다.

```python
from langchain_openai import ChatOpenAI
from vtree_search import VTreeSearchEngine, VtreeIngestor

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
search_engine = VTreeSearchEngine(config=search_config, llm=llm)
ingestor = VtreeIngestor(config=ingestion_config, llm=llm)
```

지원 대상 예시:

- `langchain-openai`: `ChatOpenAI`
- `langchain-google-genai`: `ChatGoogleGenerativeAI`
- `langchain-anthropic`: `ChatAnthropic`

## 3. 내부 처리 규칙

- 검색: 내부에서 `ainvoke` 배치 호출 후 JSON 배열(`node_id`, `keep`, `reason`)만 허용
- 적재: 내부에서 `ainvoke` 호출 후 `[TBL]...[/TBL]`, `[IMG]...[/IMG]` 형식 강제

## 4. 프롬프트 위치

- `src_py/vtree_search/ingestion/prompts/table_prompt.py`
  - `TABLE_PROMPT`
- `src_py/vtree_search/ingestion/prompts/image_prompt.py`
  - `IMAGE_PROMPT`

## 5. 실패 정책

- 형식 위반 응답(잘못된 JSON, 누락 node_id, 잘못된 태그 형식)은 즉시 실패한다.
- 자동 보정/fallback은 제공하지 않는다.

## 6. 드라이버 사용

- 검색 드라이버: `scripts/run-search.py --llm-factory module:function`
- 적재 드라이버: `scripts/run-ingestion.py --llm-factory module:function`

`module:function`은 LangChain 모델/체인을 생성해 반환해야 한다.
