"""T034: 서버 없이 열리는 report.html (FR-016, SC-006)."""
import json
import re

from src.build_static import build_report


def make_results(tmp_path, ids, memo="프론트범퍼 도색 필요."):
    def one(i):
        return {"inspection_id": i, "memo": memo, "sentences": [{"idx": 0, "text": memo, "role": "반영"}],
                "overall": "정상", "items": [], "excluded": [], "warnings": [],
                "meta": {"model": "m", "knowledge": "base", "attempts": 1, "failure": None, "cost_usd": 0.1}}
    for name in ("base", "extended"):
        (tmp_path / f"results_{name}.json").write_text(json.dumps({
            "model": "m", "knowledge": name, "generated_at": "2026-11-09T00:00:00+00:00", "cost_usd": 0.1,
            "catalog": {"BP-FR-PT": {"name": "프론트범퍼 도색", "part": "프론트범퍼", "price": 180000, "note": ""}},
            "results": [one(i) for i in ids]}, ensure_ascii=False), encoding="utf-8")


HTML = "<script>\nconst EMBEDDED = /*__EMBEDDED__*/null;\n</script>"


def build(tmp_path, ids=("INS-001", "INS-002"), memo="프론트범퍼 도색 필요."):
    make_results(tmp_path, ids, memo)
    html = tmp_path / "index.html"
    html.write_text(HTML, encoding="utf-8")
    out = tmp_path / "report.html"
    build_report(tmp_path, html, out)
    return out.read_text(encoding="utf-8")


def test_report_embeds_results_and_has_no_external_requests(tmp_path):
    text = build(tmp_path)
    assert "/*__EMBEDDED__*/null" not in text
    assert "const EMBEDDED = {" in text
    assert not re.search(r"https?://", text)


def test_report_has_all_inspections(tmp_path):
    ids = [f"INS-{n:03d}" for n in range(1, 11)]
    text = build(tmp_path, ids)
    for i in ids:
        assert i in text


def test_embedded_data_cannot_break_out_of_script_tag(tmp_path):
    text = build(tmp_path, memo="</script><img src=x onerror=alert(1)>")
    assert text.count("</script>") == 1
