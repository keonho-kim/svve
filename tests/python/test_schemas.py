import numpy as np
import pytest

from svve_core.schemas import SearchRequest


def test_search_request_normalizes_query_dtype_and_shape() -> None:
    request = SearchRequest(query=[1, 2, 3], top_k=5)

    assert request.query.ndim == 1
    assert request.query.dtype == np.float32
    assert request.query.flags.c_contiguous
    assert request.top_k == 5


def test_search_request_rejects_non_1d_query() -> None:
    with pytest.raises(ValueError, match="query must be a 1D numpy array"):
        SearchRequest(query=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32), top_k=3)
