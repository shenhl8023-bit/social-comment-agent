import json

from social_comment_agent.watcher import scan_once


def test_watcher_processes_new_file_once(tmp_path):
    inbox = tmp_path / "inbox"
    archive = tmp_path / "archive"
    state = tmp_path / "state.json"
    inbox.mkdir()
    (inbox / "comments.jsonl").write_text(
        json.dumps({"text": "加载太慢，希望优化", "id": "1"}, ensure_ascii=False),
        encoding="utf-8",
    )

    first = scan_once(inbox, archive, state, platform="demo")
    second = scan_once(inbox, archive, state, platform="demo")

    assert len(first) == 1
    assert first[0]["markdown"]
    assert len(second) == 0
    assert state.exists()
