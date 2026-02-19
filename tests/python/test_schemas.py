import numpy as np

from svve_core.schemas import SearchRequest


def test_search_request_normalizes_query_dtype_and_shape() -> None:
    request = SearchRequest(query=[1, 2, 3], top_k=5)

    assert request.query.ndim == 1
    assert request.query.dtype == np.float32
    assert request.top_k == 5
