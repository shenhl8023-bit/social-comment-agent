import json

from social_comment_agent.collector import dedupe_comments, load_comments, normalize_comment


def test_normalize_comment_supports_chinese_keys():
    c = normalize_comment({"评论内容": "希望加导出", "评论ID": "1", "用户名": "张三", "点赞数": "3"}, platform="xhs")
    assert c.text == "希望加导出"
    assert c.comment_id == "1"
    assert c.metrics["点赞数"] == 3


def test_load_comments_jsonl(tmp_path):
    p = tmp_path / "comments.jsonl"
    p.write_text(json.dumps({"text": "加载慢", "id": "a"}, ensure_ascii=False) + "\n", encoding="utf-8")
    comments = load_comments(p, platform="demo")
    assert len(comments) == 1
    assert comments[0].platform == "demo"


def test_dedupe_comments_removes_duplicates():
    c1 = normalize_comment({"text": "加载慢", "id": "a"}, platform="demo")
    c2 = normalize_comment({"text": "加载慢", "id": "a"}, platform="demo")
    assert len(dedupe_comments([c1, c2])) == 1
