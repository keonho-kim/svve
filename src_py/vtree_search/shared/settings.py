"""
목적:
- 프로젝트 기본 메타 설정을 제공한다.

설명:
- 문서/로그/진단에서 공통으로 사용할 식별자 정보를 유지한다.

디자인 패턴:
- 값 객체(Value Object).

참조:
- README.md
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectSettings(BaseModel):
    """Vtree Search 기본 메타 설정 모델."""

    project_name: str = Field(default="Vtree Search")
    python_package: str = Field(default="vtree_search")
    rust_module: str = Field(default="_vtree_search")
    phase: str = Field(default="phase2-runtime")


def default_settings() -> ProjectSettings:
    """기본 설정 객체를 생성한다."""
    return ProjectSettings()
