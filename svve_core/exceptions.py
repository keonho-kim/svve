class SVVEError(Exception):
    """svve_core 공통 예외."""


class QueryValidationError(SVVEError):
    """검색 쿼리 입력이 유효하지 않을 때 발생."""


class SearchExecutionError(SVVEError):
    """Rust 검색 코어 실행 중 오류가 발생할 때 사용."""
