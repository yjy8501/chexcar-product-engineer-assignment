"""저장된 결과를 web/index.html에 끼워 넣어, 서버와 CLI 없이 열리는 report.html을 만든다. `python -m src.build_static` (FR-016)"""
import json
from pathlib import Path

from .config import RESULTS, WEB, ROOT

MARKER = "/*__EMBEDDED__*/null"
EXTRA_MARKER = "/*__EXTRA__*/null"


def _js(data) -> str:
    """script 태그 안에 안전하게 넣을 JSON. '</script>'로 태그를 닫는 입력이 있어도 깨지지 않게 한다."""
    return (json.dumps(data, ensure_ascii=False)
            .replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build_report(results_dir: Path, html_path: Path, out_path: Path, extra: dict | None = None) -> Path:
    embedded = {}
    for p in sorted(Path(results_dir).glob("results_*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        embedded[payload["knowledge"]] = payload
    html = Path(html_path).read_text(encoding="utf-8")
    assert MARKER in html, "web/index.html에 끼워 넣을 자리가 없다"
    html = html.replace(MARKER, _js(embedded))
    if extra is not None and EXTRA_MARKER in html:
        html = html.replace(EXTRA_MARKER, _js(extra))
    Path(out_path).write_text(html, encoding="utf-8")
    return Path(out_path)


def main() -> int:
    from .app import summary
    out = build_report(RESULTS, WEB / "index.html", ROOT / "report.html", extra=summary())
    print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
