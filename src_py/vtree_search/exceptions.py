"""
목적:
- Vtree Search Python 계층의 예외 타입을 표준화한다.

설명:
- 큐 상태, 잡 상태, 의존성 오류를 명시적으로 구분해
  라이브러리 소비자가 처리 전략을 선택할 수 있게 한다.

디자인 패턴:
- 계층형 예외(Hierarchical Exception).

참조:
- src_py/vtree_search/search/engine.py
- src_py/vtree_search/runtime/bridge.py
"""


class VtreeSearchError(Exception):
    """Vtree Search 공통 베이스 예외."""


class ConfigurationError(VtreeSearchError):
    """설정값이 유효하지 않을 때 발생한다."""


class QueueOverloadedError(VtreeSearchError):
    """큐 포화 상태로 작업을 수용할 수 없을 때 발생한다."""


class JobNotFoundError(VtreeSearchError):
    """잡 ID를 찾을 수 없을 때 발생한다."""


class JobExpiredError(VtreeSearchError):
    """잡 결과 TTL이 만료되어 조회할 수 없을 때 발생한다."""


class JobFailedError(VtreeSearchError):
    """잡이 실패 상태로 종료되었을 때 발생한다."""


class DependencyUnavailableError(VtreeSearchError):
    """Redis/Rust 확장 등 필수 의존성을 사용할 수 없을 때 발생한다."""


class IngestionProcessingError(VtreeSearchError):
    """문서 파싱/주석/청킹 단계에서 오류가 발생할 때 사용한다."""
