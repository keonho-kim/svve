from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import ValidationError

from .exceptions import QueryValidationError
from .schemas import SearchRequest

if TYPE_CHECKING:
    from . import _svve_core


class SearchEngine:
    def __init__(self, index_root: str) -> None:
        from . import _svve_core

        self._inner = _svve_core.SearchEngine(index_root)

    @property
    def index_root(self) -> str:
        return self._inner.index_root

    def search(
        self,
        query: ArrayLike,
        top_k: int = 10,
    ) -> tuple[NDArray[np.uint32], NDArray[np.float32]]:
        try:
            request = SearchRequest(query=query, top_k=top_k)
        except ValidationError as exc:
            raise QueryValidationError(str(exc)) from exc

        ids, scores = self._inner.search(request.query, request.top_k)
        return (
            np.asarray(ids, dtype=np.uint32),
            np.asarray(scores, dtype=np.float32),
        )
