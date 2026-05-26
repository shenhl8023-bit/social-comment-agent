from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Any

from .models import Comment


TEXT_KEYS = ("text", "content", "comment", "body", "message", "评论", "内容", "评论内容", "消息内容", "反馈内容", "评价内容")
ID_KEYS = ("comment_id", "id", "评论ID", "评论id", "cid", "rpid", "mid", "评价ID", "review_id", "消息ID")
AUTHOR_KEYS = ("author", "user", "nickname", "用户名", "用户昵称", "昵称", "作者", "发送人", "会员名")
POST_KEYS = ("post_id", "aweme_id", "note_id", "video_id", "帖子ID", "笔记ID", "视频ID", "作品ID", "微博ID", "稿件ID", "应用ID", "群ID")
TIME_KEYS = ("created_at", "time", "date", "发布时间", "评论时间", "创建时间", "发送时间", "评价时间")


def _first(row: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def normalize_comment(row: dict[str, Any], platform: str = "unknown") -> Comment:
    text = _first(row, TEXT_KEYS)
    if not text:
        raise ValueError("comment text is required")
    metrics: dict[str, int] = {}
    for key in ("likes", "like_count", "点赞数", "digg_count", "like", "replies", "reply_count", "回复数", "rating", "评分"):
        if key in row:
            try:
                metrics[key] = int(row[key])
            except (TypeError, ValueError):
                pass
    return Comment(
        platform=str(row.get("platform") or platform),
        post_id=_first(row, POST_KEYS, "unknown_post"),
        comment_id=_first(row, ID_KEYS, f"generated_{abs(hash(text))}"),
        author=_first(row, AUTHOR_KEYS, "anonymous"),
        text=text,
        created_at=_first(row, TIME_KEYS),
        metrics=metrics,
        raw=dict(row),
    )


def load_comments(path: str | Path, platform: str = "unknown") -> list[Comment]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("comments", [])
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        raise ValueError(f"unsupported input format: {suffix}; use .jsonl/.json/.csv")
    return [normalize_comment(row, platform=platform) for row in rows]


def dedupe_comments(comments: Iterable[Comment]) -> list[Comment]:
    seen: set[tuple[str, str, str]] = set()
    result: list[Comment] = []
    for comment in comments:
        key = (comment.platform, comment.comment_id, comment.normalized_text())
        if key not in seen:
            seen.add(key)
            result.append(comment)
    return result
