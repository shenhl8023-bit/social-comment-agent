from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PRIORITY_RANK = {"P0": 3, "P1": 2, "P2": 1}


def build_knowledge_base(archive_dir: str | Path, out_dir: str | Path) -> dict[str, Path]:
    """Build a searchable local index from archived PM insight reports."""
    archive_path = Path(archive_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for report_path in sorted(archive_path.rglob("pm_insights.json")):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        generated_at = str(report.get("generated_at", ""))
        for insight in report.get("insights", []):
            evidence_texts = [
                str(item.get("text", "")).strip()
                for item in insight.get("evidence", [])
                if str(item.get("text", "")).strip()
            ]
            title = str(insight.get("title", "未命名洞察"))
            entry = {
                "id": _entry_id(report_path, title),
                "title": title,
                "priority": str(insight.get("priority", "")),
                "score": float(insight.get("score", 0) or 0),
                "problem": str(insight.get("problem", "")),
                "user_value": str(insight.get("user_value", "")),
                "suggested_solution": str(insight.get("suggested_solution", "")),
                "evidence_texts": evidence_texts,
                "generated_at": generated_at,
                "source_report": str(report_path),
                "source_dir": str(report_path.parent),
                "search_text": _join_search_text(insight, evidence_texts),
            }
            entries.append(entry)

    entries.sort(key=lambda e: (e.get("generated_at", ""), PRIORITY_RANK.get(e.get("priority", ""), 0), e.get("score", 0)), reverse=True)
    index = {"entries": entries}

    json_path = out_path / "knowledge_base.json"
    markdown_path = out_path / "knowledge_base.md"
    json_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_knowledge_base_markdown(entries), encoding="utf-8")
    return {"index_json": json_path, "index_markdown": markdown_path}


def search_knowledge_base(index_path: str | Path, query: str, limit: int = 10) -> list[dict[str, Any]]:
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    terms = _terms(query)
    if not terms:
        return []

    results: list[dict[str, Any]] = []
    for entry in index.get("entries", []):
        text = str(entry.get("search_text", "")).lower()
        matched_terms = [term for term in terms if term in text]
        if not matched_terms:
            continue
        result = dict(entry)
        result["match_count"] = len(matched_terms)
        result["matched_terms"] = matched_terms
        results.append(result)

    results.sort(
        key=lambda e: (
            e["match_count"],
            PRIORITY_RANK.get(e.get("priority", ""), 0),
            float(e.get("score", 0) or 0),
            e.get("generated_at", ""),
        ),
        reverse=True,
    )
    return results[:limit]


def _entry_id(report_path: Path, title: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title).strip("-") or "insight"
    return f"{report_path.parent.name}-{slug}"


def _join_search_text(insight: dict[str, Any], evidence_texts: list[str]) -> str:
    parts = [
        insight.get("title", ""),
        insight.get("problem", ""),
        insight.get("user_value", ""),
        insight.get("suggested_solution", ""),
        *evidence_texts,
    ]
    return "\n".join(str(part) for part in parts if str(part).strip())


def _terms(query: str) -> list[str]:
    return [term.lower() for term in re.split(r"\s+", query.strip()) if term.strip()]


def _knowledge_base_markdown(entries: list[dict[str, Any]]) -> str:
    lines = ["# PM 洞察知识库", "", f"洞察条目数：{len(entries)}", ""]
    for idx, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"## {idx}. {entry['title']}（{entry.get('priority', '')}，score={entry.get('score', 0)}）",
                "",
                f"- 来源：{entry.get('source_report', '')}",
                f"- 生成时间：{entry.get('generated_at', '')}",
                f"- 问题：{entry.get('problem', '')}",
                f"- 用户价值：{entry.get('user_value', '')}",
                f"- 建议方案：{entry.get('suggested_solution', '')}",
                "- 证据评论：",
            ]
        )
        for evidence in entry.get("evidence_texts", [])[:3]:
            lines.append(f"  - {evidence}")
        lines.append("")
    return "\n".join(lines)
