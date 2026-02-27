"""
목적:
- 공통 설정/유틸 공개 심볼을 정의한다.

설명:
- 패키지 전역 기본값을 중앙에서 재사용하기 위한 진입점이다.

디자인 패턴:
- 설정 객체(Configuration Object).

참조:
- src_py/vtree_search/shared/settings.py
"""

from .settings import ProjectSettings, default_settings

__all__ = ["ProjectSettings", "default_settings"]
