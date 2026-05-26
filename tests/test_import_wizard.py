import json

from social_comment_agent.import_wizard import format_preview, preview_import


def test_import_wizard_previews_csv_with_aliases(tmp_path):
    p = tmp_path / "export.csv"
    p.write_text(
        "内容,用户昵称,发布时间,video_id,id,platform\n"
        "加载很慢,张三,2026-05-01,v1,c1,douyin\n"
        "加载很慢,张三,2026-05-01,v1,c1,douyin\n",
        encoding="utf-8",
    )

    preview = preview_import(p)
    text = format_preview(preview)

    assert preview.format == "csv"
    assert preview.total_rows == 2
    assert preview.recognizable_comments == 2
    assert preview.unique_comments == 1
    assert preview.field_mapping["text"] == "内容"
    assert preview.field_mapping["post_id"] == "video_id"
    assert "检测到 1 条重复评论" in text
    assert "可以放入 data/inbox/" in text


def test_import_wizard_previews_json_comments_object(tmp_path):
    p = tmp_path / "export.json"
    p.write_text(
        json.dumps({"comments": [{"message": "希望支持批量导出", "comment_id": "c1"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    preview = preview_import(p, platform="wechat_group")
    text = format_preview(preview)

    assert preview.format == "json"
    assert preview.recognizable_comments == 1
    assert preview.field_mapping["text"] == "message"
    assert "未识别 platform 字段，将使用默认平台名：wechat_group" in text


def test_import_wizard_previews_jsonl_and_skips_missing_text(tmp_path):
    p = tmp_path / "export.jsonl"
    p.write_text(
        "\n".join([
            json.dumps({"body": "客服回复慢", "id": "ok"}, ensure_ascii=False),
            json.dumps({"id": "missing-text"}, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )

    preview = preview_import(p)
    text = format_preview(preview)

    assert preview.format == "jsonl"
    assert preview.total_rows == 2
    assert preview.recognizable_comments == 1
    assert preview.skipped_rows == 1
    assert "1 行跳过：comment text is required" in text
    assert "跳过行数：1" in text


def test_import_wizard_warns_when_text_field_is_unrecognized(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("foo,bar\n1,2\n", encoding="utf-8")

    preview = preview_import(p)
    text = format_preview(preview)

    assert preview.recognizable_comments == 0
    assert "未识别评论内容字段" in text
    assert "请先补充或映射评论内容字段" in text
