from social_comment_agent.models import AnalysisReport, Comment, Insight


def test_comment_normalized_text():
    c = Comment(platform="x", post_id="p", comment_id="c", author="a", text="  太   慢了  ")
    assert c.normalized_text() == "太 慢了"


def test_report_create_has_total_and_summary():
    report = AnalysisReport.create(total_comments=1, insights=[], summary="ok")
    assert report.total_comments == 1
    assert report.summary == "ok"
    assert "T" in report.generated_at
