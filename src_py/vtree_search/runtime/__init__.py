"""
목적:
- Rust FFI 런타임 브릿지 계층의 공개 진입점을 제공한다.

설명:
- Python 클래스는 Rust 브릿지를 직접 import하지 않고 본 래퍼를 통해 호출한다.

디자인 패턴:
- 파사드(Facade).

참조:
- src_py/vtree_search/runtime/bridge.py
"""

from .bridge import RustRuntimeBridge

__all__ = ["RustRuntimeBridge"]
