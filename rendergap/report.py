"""Human-readable and machine-readable output."""

from __future__ import annotations

import csv
import io
import json

from .diff import GapReport
from .score import score_report

BADGE = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}


def _cell(text: str) -> str:
    """Escape a value so it cannot break out of a Markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _line(text: str) -> str:
    """Outside a table a pipe is just a pipe: only collapse newlines."""
    return " ".join((text or "").split())


def markdown_report(reports: list[GapReport]) -> str:
    out: list[str] = ["# render-gap — what a non-JavaScript crawler misses", ""]
    out.append(
        "GPTBot, OAI-SearchBot, PerplexityBot, Claude-SearchBot and Google-Extended "
        "do not run JavaScript. Everything listed below exists in a browser and not "
        "in the HTML your server returns."
    )
    out.append("")

    out.append("| Page | Score | Verdict | Served words | Rendered words | Missing |")
    out.append("|---|---:|---|---:|---:|---:|")
    for r in reports:
        s = score_report(r)
        out.append(
            f"| {_cell(s['url'])} | {s['score']}/100 | {s['verdict']} | "
            f"{s['raw_words']} | {s['rendered_words']} | {s['missing_word_pct']}% |"
        )
    out.append("")

    for r in reports:
        s = score_report(r)
        out.append(f"## {_line(s['url'])} — {s['score']}/100 ({s['verdict']})")
        out.append("")
        out.append(s["message"])
        out.append("")
        if not s["gaps"]:
            out.append("No gap found: the served HTML carries the whole page.")
            out.append("")
            continue
        for g in s["gaps"]:
            out.append(f"- {BADGE[g['severity']]} **{g['field']}** — {_line(g['summary'])}")
            if g["detail"]:
                out.append(f"  - {_line(g['detail'])}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def json_report(reports: list[GapReport]) -> str:
    return json.dumps([score_report(r) for r in reports], indent=2, ensure_ascii=False) + "\n"


def csv_report(reports: list[GapReport]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["url", "score", "verdict", "field", "severity", "points", "summary", "detail"])
    for r in reports:
        s = score_report(r)
        if not s["gaps"]:
            w.writerow([s["url"], s["score"], s["verdict"], "", "", "", "no gap", ""])
        for g in s["gaps"]:
            w.writerow([
                s["url"], s["score"], s["verdict"],
                g["field"], g["severity"], g["points"], g["summary"], g["detail"],
            ])
    return buf.getvalue()
