from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .collector import AUTHOR_KEYS, ID_KEYS, POST_KEYS, TEXT_KEYS, TIME_KEYS, dedupe_comments, normalize_comment
from .platform_templates import PlatformTemplate, get_platform_template, list_platform_templates

PLATFORM_KEYS = ("platform", "source", "来源", "平台")
METRIC_KEYS = ("likes", "like_count", "点赞数", "replies", "reply_count", "评分", "rating")
EXTRA_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "url": ("url", "链接", "来源链接", "笔记链接", "视频链接", "作品链接", "微博链接"),
    "rating": ("rating", "评分", "star"),
    "version": ("version", "版本", "app_version"),
}
FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "text": TEXT_KEYS,
    "comment_id": ID_KEYS,
    "author": AUTHOR_KEYS,
    "post_id": POST_KEYS,
    "created_at": TIME_KEYS,
    "platform": PLATFORM_KEYS,
    **EXTRA_FIELD_GROUPS,
}


@dataclass(frozen=True)
class ImportPreview:
    path: Path
    format: str
    total_rows: int
    recognizable_comments: int
    unique_comments: int
    field_mapping: dict[str, str]
    warnings: list[str]
    suggestions: list[str]
    template_name: str | None = None
    template_display_name: str | None = None
    missing_recommended_fields: tuple[str, ...] = ()

    @property
    def skipped_rows(self) -> int:
        return max(self.total_rows - self.recognizable_comments, 0)

    @property
    def duplicate_rows(self) -> int:
        return max(self.recognizable_comments - self.unique_comments, 0)


def _load_raw_rows(path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL line {line_number} must be an object")
            rows.append(value)
        return "jsonl", rows
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("comments", [])
        else:
            raise ValueError("JSON input must be a list or an object with comments")
        if not isinstance(rows, list):
            raise ValueError("JSON comments must be a list")
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("JSON comments entries must be objects")
        return "json", rows
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return "csv", list(csv.DictReader(f))
    raise ValueError(f"unsupported input format: {suffix}; use .jsonl/.json/.csv")


def _first_present_key(rows: list[dict[str, Any]], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        for row in rows:
            if alias in row and row.get(alias) not in (None, ""):
                return alias
    return None


def _merge_field_groups(template: PlatformTemplate | None = None) -> dict[str, tuple[str, ...]]:
    groups = dict(FIELD_GROUPS)
    if not template:
        return groups
    for logical_name, aliases in template.field_aliases.items():
        existing = groups.get(logical_name, ())
        groups[logical_name] = tuple(dict.fromkeys((*aliases, *existing)))
    return groups


def detect_field_mapping(rows: list[dict[str, Any]], template: PlatformTemplate | None = None) -> dict[str, str]:
    return {
        logical_name: key
        for logical_name, aliases in _merge_field_groups(template).items()
        if (key := _first_present_key(rows, aliases))
    }


def _rename_row_with_template(row: dict[str, Any], field_mapping: dict[str, str]) -> dict[str, Any]:
    normalized = dict(row)
    canonical_keys = {
        "text": "text",
        "comment_id": "comment_id",
        "author": "author",
        "post_id": "post_id",
        "created_at": "created_at",
        "platform": "platform",
        "likes": "likes",
        "replies": "replies",
    }
    for logical_name, canonical_key in canonical_keys.items():
        source_key = field_mapping.get(logical_name)
        if source_key and canonical_key not in normalized:
            normalized[canonical_key] = row.get(source_key)
    return normalized


def _missing_recommended_fields(rows: list[dict[str, Any]], template: PlatformTemplate | None) -> tuple[str, ...]:
    if not template or not rows:
        return ()
    available = set().union(*(row.keys() for row in rows))
    return tuple(field for field in template.recommended_fields if field not in available)


def preview_import(
    path: str | Path,
    platform: str = "unknown",
    platform_template: str | PlatformTemplate | None = None,
) -> ImportPreview:
    source = Path(path)
    fmt, rows = _load_raw_rows(source)
    template = get_platform_template(platform_template) if isinstance(platform_template, str) else platform_template
    effective_platform = template.default_platform if template and platform == "unknown" else platform
    field_mapping = detect_field_mapping(rows, template=template)
    warnings: list[str] = []
    suggestions: list[str] = []
    comments = []
    error_counter: Counter[str] = Counter()

    for row in rows:
        try:
            comments.append(normalize_comment(_rename_row_with_template(row, field_mapping), platform=effective_platform))
        except ValueError as exc:
            error_counter[str(exc)] += 1

    unique_comments = dedupe_comments(comments)
    missing_recommended_fields = _missing_recommended_fields(rows, template)

    if not rows:
        warnings.append("文件没有可读取的数据行")
    if "text" not in field_mapping:
        warnings.append("未识别评论内容字段，必须包含 text/content/comment/body/message/评论/内容/评论内容 等字段之一")
    if error_counter:
        for message, count in error_counter.most_common():
            warnings.append(f"{count} 行跳过：{message}")
    if "platform" not in field_mapping:
        warnings.append(f"未识别 platform 字段，将使用默认平台名：{effective_platform}")
    if "comment_id" not in field_mapping:
        warnings.append("未识别 comment_id 字段，将按评论内容生成稳定性较弱的 ID")
    if len(unique_comments) < len(comments):
        warnings.append(f"检测到 {len(comments) - len(unique_comments)} 条重复评论，流水线会自动去重")
    if missing_recommended_fields:
        warnings.append("模板推荐字段缺失：" + "、".join(missing_recommended_fields))

    if template:
        suggestions.append(f"已应用平台模板：{template.display_name}（{template.name}）")
        suggestions.extend(template.notes)
    if comments:
        suggestions.append("可以放入 data/inbox/ 由 watcher 自动处理")
    else:
        suggestions.append("请先补充或映射评论内容字段，再放入 data/inbox/")
    if "created_at" not in field_mapping:
        suggestions.append("建议导出发布时间字段，便于后续按时间分析趋势")
    if "post_id" not in field_mapping:
        suggestions.append("建议导出内容/帖子/视频 ID，便于按来源内容聚合需求")

    return ImportPreview(
        path=source,
        format=fmt,
        total_rows=len(rows),
        recognizable_comments=len(comments),
        unique_comments=len(unique_comments),
        field_mapping=field_mapping,
        warnings=warnings,
        suggestions=suggestions,
        template_name=template.name if template else None,
        template_display_name=template.display_name if template else None,
        missing_recommended_fields=missing_recommended_fields,
    )


def format_preview(preview: ImportPreview) -> str:
    lines = [
        "社交评论导入预检",
        "",
        f"文件：{preview.path}",
        f"格式：{preview.format}",
    ]
    if preview.template_display_name:
        lines.append(f"平台模板：{preview.template_display_name}（{preview.template_name}）")
    lines.extend([
        f"总行数：{preview.total_rows}",
        f"可识别评论数：{preview.recognizable_comments}",
        f"去重后评论数：{preview.unique_comments}",
    ])
    if preview.skipped_rows:
        lines.append(f"跳过行数：{preview.skipped_rows}")
    if preview.duplicate_rows:
        lines.append(f"重复行数：{preview.duplicate_rows}")

    lines.extend(["", "识别字段："])
    if preview.field_mapping:
        for logical_name in (
            "text",
            "author",
            "created_at",
            "post_id",
            "comment_id",
            "platform",
            "likes",
            "replies",
            "rating",
            "version",
            "url",
        ):
            if logical_name in preview.field_mapping:
                lines.append(f"- {logical_name}: {preview.field_mapping[logical_name]}")
    else:
        lines.append("- 未识别")

    lines.extend(["", "风险："])
    if preview.warnings:
        lines.extend(f"- {warning}" for warning in preview.warnings)
    else:
        lines.append("- 未发现明显风险")

    lines.extend(["", "建议："])
    lines.extend(f"- {suggestion}" for suggestion in preview.suggestions)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview whether an authorized social-comment export can be imported")
    parser.add_argument("input", nargs="?", help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--platform", default="unknown", help="Default platform name when the file has no platform column")
    parser.add_argument("--platform-template", help="Apply a known platform export template, e.g. douyin/xiaohongshu/bilibili")
    parser.add_argument("--list-platform-templates", action="store_true", help="List bundled platform templates and exit")
    args = parser.parse_args()
    if args.list_platform_templates:
        for template in list_platform_templates():
            print(f"{template.name}\t{template.display_name}\t{template.description}")
        return
    if not args.input:
        parser.error("input is required unless --list-platform-templates is used")
    print(format_preview(preview_import(args.input, platform=args.platform, platform_template=args.platform_template)))


if __name__ == "__main__":
    main()
