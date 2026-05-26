from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .collector import AUTHOR_KEYS, ID_KEYS, POST_KEYS, TEXT_KEYS, TIME_KEYS, dedupe_comments, normalize_comment

PLATFORM_KEYS = ("platform", "source", "来源", "平台")
FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "text": TEXT_KEYS,
    "comment_id": ID_KEYS,
    "author": AUTHOR_KEYS,
    "post_id": POST_KEYS,
    "created_at": TIME_KEYS,
    "platform": PLATFORM_KEYS,
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


def detect_field_mapping(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        logical_name: key
        for logical_name, aliases in FIELD_GROUPS.items()
        if (key := _first_present_key(rows, aliases))
    }


def preview_import(path: str | Path, platform: str = "unknown") -> ImportPreview:
    source = Path(path)
    fmt, rows = _load_raw_rows(source)
    field_mapping = detect_field_mapping(rows)
    warnings: list[str] = []
    suggestions: list[str] = []
    comments = []
    error_counter: Counter[str] = Counter()

    for row in rows:
        try:
            comments.append(normalize_comment(row, platform=platform))
        except ValueError as exc:
            error_counter[str(exc)] += 1

    unique_comments = dedupe_comments(comments)

    if not rows:
        warnings.append("文件没有可读取的数据行")
    if "text" not in field_mapping:
        warnings.append("未识别评论内容字段，必须包含 text/content/comment/body/message/评论/内容/评论内容 等字段之一")
    if error_counter:
        for message, count in error_counter.most_common():
            warnings.append(f"{count} 行跳过：{message}")
    if "platform" not in field_mapping:
        warnings.append(f"未识别 platform 字段，将使用默认平台名：{platform}")
    if "comment_id" not in field_mapping:
        warnings.append("未识别 comment_id 字段，将按评论内容生成稳定性较弱的 ID")
    if len(unique_comments) < len(comments):
        warnings.append(f"检测到 {len(comments) - len(unique_comments)} 条重复评论，流水线会自动去重")

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
    )


def format_preview(preview: ImportPreview) -> str:
    lines = [
        "社交评论导入预检",
        "",
        f"文件：{preview.path}",
        f"格式：{preview.format}",
        f"总行数：{preview.total_rows}",
        f"可识别评论数：{preview.recognizable_comments}",
        f"去重后评论数：{preview.unique_comments}",
    ]
    if preview.skipped_rows:
        lines.append(f"跳过行数：{preview.skipped_rows}")
    if preview.duplicate_rows:
        lines.append(f"重复行数：{preview.duplicate_rows}")

    lines.extend(["", "识别字段："])
    if preview.field_mapping:
        for logical_name in ("text", "author", "created_at", "post_id", "comment_id", "platform"):
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
    parser.add_argument("input", help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--platform", default="unknown", help="Default platform name when the file has no platform column")
    args = parser.parse_args()
    print(format_preview(preview_import(args.input, platform=args.platform)))


if __name__ == "__main__":
    main()
