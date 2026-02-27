"""
목적:
- 적재 엔진의 이전 경로 호환 진입점을 유지한다.

설명:
- `IngestionPipeline` 명칭은 `VtreeIngestor`로 통합되었고,
  이 파일은 명시적 별칭만 제공한다.

디자인 패턴:
- 호환 어댑터(Compatibility Adapter).

참조:
- src_py/vtree_search/ingestion/ingestor.py
"""

from vtree_search.ingestion.ingestor import VtreeIngestor as IngestionPipeline

__all__ = ["IngestionPipeline"]
