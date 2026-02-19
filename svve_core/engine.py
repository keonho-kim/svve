from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import ValidationError

from .exceptions import QueryValidationError, SearchExecutionError
from .schemas import SearchRequest

if TYPE_CHECKING:
    from . import _svve_core

SearchFn = Callable[[NDArray[np.float32], int], tuple[list[int], list[float], list[list[float]]]]


class SearchEngine:
    def __init__(self) -> None:
        from . import _svve_core

        self._inner = _svve_core.SearchEngine()

    def search(
        self,
        query: ArrayLike,
        top_k: int = 10,
        search_fn: SearchFn | None = None,
    ) -> tuple[NDArray[np.uint32], NDArray[np.float32]]:
        if search_fn is None:
            raise QueryValidationError("search_fn은 필수입니다")

        try:
            request = SearchRequest(query=query, top_k=top_k)
        except ValidationError as exc:
            raise QueryValidationError(str(exc)) from exc

        try:
            ids, scores = self._inner.search(request.query, request.top_k, search_fn)
        except RuntimeError as exc:
            raise SearchExecutionError(str(exc)) from exc

        return (
            np.asarray(ids, dtype=np.uint32),
            np.asarray(scores, dtype=np.float32),
        )
