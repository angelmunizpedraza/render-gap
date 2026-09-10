"""Turn a GapReport into a verdict a human can act on."""

from __future__ import annotations

from .diff import GapReport

# The crawlers that decide whether an AI answer can cite you. None of them
# execute JavaScript today, which is the whole reason this tool exists.
NON_JS_CITATION_BOTS = (
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Claude-SearchBot",
    "Claude-User",
    "Google-Extended",
    "Applebot-Extended",
    "CCBot",
)

VERDICTS = (
    (90, "clean", "A non-JS crawler sees essentially the same page a human does."),
    (70, "minor", "Most of the page is served, but some of it needs JavaScript."),
    (40, "degraded", "A meaningful part of this page does not exist for a non-JS crawler."),
    (0, "invisible", "To a non-JS crawler this page is mostly empty."),
)


def score_report(report: GapReport) -> dict:
    score = report.score
    for floor, label, sentence in VERDICTS:
        if score >= floor:
            verdict, message = label, sentence
            break
    return {
        "url": report.url,
        "score": score,
        "verdict": verdict,
        "message": message,
        "raw_words": report.raw_words,
        "rendered_words": report.rendered_words,
        "missing_word_pct": round(report.missing_word_pct, 1),
        "gaps": [g.to_dict() for g in report.sorted_gaps()],
        "affects": list(NON_JS_CITATION_BOTS),
    }
