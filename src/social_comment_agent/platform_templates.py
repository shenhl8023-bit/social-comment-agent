from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlatformTemplate:
    """Field mapping hints for one authorized platform export format."""

    name: str
    display_name: str
    description: str
    default_platform: str
    field_aliases: dict[str, tuple[str, ...]]
    recommended_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlatformTemplate":
        field_aliases = {
            str(logical_name): tuple(str(alias) for alias in aliases)
            for logical_name, aliases in data.get("field_aliases", {}).items()
        }
        return cls(
            name=str(data["name"]),
            display_name=str(data.get("display_name") or data["name"]),
            description=str(data.get("description") or ""),
            default_platform=str(data.get("default_platform") or data["name"]),
            field_aliases=field_aliases,
            recommended_fields=tuple(str(item) for item in data.get("recommended_fields", ())),
            notes=tuple(str(item) for item in data.get("notes", ())),
        )


def _template_dir() -> Path:
    return Path(str(resources.files("social_comment_agent") / "templates" / "platforms"))


@lru_cache(maxsize=1)
def load_platform_templates() -> dict[str, PlatformTemplate]:
    templates: dict[str, PlatformTemplate] = {}
    for path in sorted(_template_dir().glob("*.json")):
        template = PlatformTemplate.from_dict(json.loads(path.read_text(encoding="utf-8")))
        templates[template.name] = template
    return templates


def list_platform_templates() -> list[PlatformTemplate]:
    return list(load_platform_templates().values())


def get_platform_template(name: str | None) -> PlatformTemplate | None:
    if not name:
        return None
    templates = load_platform_templates()
    key = name.strip().lower()
    if key in templates:
        return templates[key]
    for template in templates.values():
        aliases = {template.name.lower(), template.display_name.lower(), template.default_platform.lower()}
        if key in aliases:
            return template
    available = ", ".join(sorted(templates)) or "none"
    raise ValueError(f"unknown platform template: {name}; available: {available}")
