from social_comment_agent.analyzer import DemandAnalyzer
from social_comment_agent.models import Comment


def test_analyzer_extracts_function_gap_and_priority():
    comments = [
        Comment("x", "p", "1", "u", "希望支持批量导出", metrics={"likes": 40}),
        Comment("x", "p", "2", "u", "建议加一个筛选功能", metrics={"likes": 10}),
    ]
    report = DemandAnalyzer().analyze(comments)
    titles = [i.title for i in report.insights]
    assert "功能缺口" in titles
    gap = next(i for i in report.insights if i.title == "功能缺口")
    assert gap.priority in {"P0", "P1"}
    assert gap.evidence


def test_analyzer_handles_no_theme():
    report = DemandAnalyzer().analyze([Comment("x", "p", "1", "u", "不错")])
    assert report.insights == []
    assert "未发现" in report.summary
