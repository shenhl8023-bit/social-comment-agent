import json

from social_comment_agent.import_wizard import format_preview, preview_import
from social_comment_agent.platform_templates import get_platform_template, list_platform_templates


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


def test_platform_template_library_loads_expected_templates():
    names = {template.name for template in list_platform_templates()}

    assert {"xiaohongshu", "bilibili", "douyin", "weibo", "app_store", "wechat_group"}.issubset(names)
    xiaohongshu = get_platform_template("小红书")
    assert xiaohongshu is not None
    assert xiaohongshu.name == "xiaohongshu"


def test_import_wizard_applies_platform_template_for_xiaohongshu(tmp_path):
    p = tmp_path / "xiaohongshu.csv"
    p.write_text(
        "评论内容,用户昵称,评论时间,笔记ID,评论ID,点赞数\n"
        "能不能加批量导出,小明,2026-05-20,note-1,c-1,12\n",
        encoding="utf-8",
    )

    preview = preview_import(p, platform_template="xiaohongshu")
    text = format_preview(preview)

    assert preview.template_name == "xiaohongshu"
    assert preview.field_mapping["text"] == "评论内容"
    assert preview.field_mapping["likes"] == "点赞数"
    assert preview.recognizable_comments == 1
    assert "平台模板：小红书（xiaohongshu）" in text
    assert "已应用平台模板：小红书（xiaohongshu）" in text
    assert "未识别 platform 字段，将使用默认平台名：xiaohongshu" in text


def test_import_wizard_reports_missing_recommended_template_fields(tmp_path):
    p = tmp_path / "douyin.csv"
    p.write_text(
        "评论内容,用户昵称\n"
        "充值后额度没到账,张三\n",
        encoding="utf-8",
    )

    preview = preview_import(p, platform_template="douyin")
    text = format_preview(preview)

    assert "评论时间" in preview.missing_recommended_fields
    assert "模板推荐字段缺失" in text
    assert "评论时间" in text
    assert preview.recognizable_comments == 1
