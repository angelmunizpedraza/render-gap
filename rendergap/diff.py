"""Compare what the server sent with what the browser ended up showing."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

from .extract import Snapshot, words

# How much each kind of gap costs, out of 100.
WEIGHTS = {
    "title": 10,
    "meta_description": 5,
    "canonical": 6,
    "h1": 12,
    "headings": 10,
    "body_text": 25,
    "paragraphs": 12,
    "jsonld": 12,
    "links": 8,
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Below this ratio of shared words, two strings are different strings.
SAME_STRING = 0.92


def _similar(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


@dataclass
class Gap:
    """One thing a browser can see and a non-JS crawler cannot."""

    field: str
    severity: str
    points: float
    summary: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "severity": self.severity,
            "points": round(self.points, 1),
            "summary": self.summary,
            "detail": self.detail,
        }


@dataclass
class GapReport:
    url: str
    raw: Snapshot
    rendered: Snapshot
    gaps: list[Gap] = field(default_factory=list)

    @property
    def raw_words(self) -> int:
        return self.raw.word_count

    @property
    def rendered_words(self) -> int:
        return self.rendered.word_count

    @property
    def missing_word_pct(self) -> float:
        """Share of the browser's body text that never reaches a non-JS crawler."""
        if self.rendered_words == 0:
            return 0.0
        missing = max(0, self.rendered_words - self.raw_words)
        return 100.0 * missing / self.rendered_words

    @property
    def lost_points(self) -> float:
        return sum(g.points for g in self.gaps)

    @property
    def score(self) -> int:
        """100 = a non-JS crawler sees everything a browser sees."""
        return max(0, min(100, round(100 - self.lost_points)))

    def sorted_gaps(self) -> list[Gap]:
        return sorted(self.gaps, key=lambda g: (SEVERITY_ORDER[g.severity], -g.points))


def _missing_items(raw: list[str], rendered: list[str]) -> list[str]:
    """Items present in the rendered list that no raw item matches."""
    pool = list(raw)
    missing: list[str] = []
    for item in rendered:
        hit = next((r for r in pool if _similar(r, item) >= SAME_STRING), None)
        if hit is None:
            missing.append(item)
        else:
            pool.remove(hit)
    return missing


def compare(raw: Snapshot, rendered: Snapshot, url: str = "") -> GapReport:
    """Build the gap report for one page.

    Only content that the browser has and the raw response lacks counts as a
    gap. Content the raw response has and the browser dropped is not a crawler
    problem, so it is ignored on purpose.
    """
    report = GapReport(url=url or rendered.url or raw.url, raw=raw, rendered=rendered)
    add = report.gaps.append

    if rendered.title and not raw.title:
        add(Gap("title", "critical", WEIGHTS["title"],
                "The <title> is written by JavaScript.",
                f"Rendered title: {rendered.title!r}"))
    elif rendered.title and _similar(raw.title, rendered.title) < SAME_STRING:
        add(Gap("title", "high", WEIGHTS["title"] * 0.6,
                "The <title> changes after JavaScript runs.",
                f"raw: {raw.title!r} / rendered: {rendered.title!r}"))

    if rendered.meta_description and not raw.meta_description:
        add(Gap("meta_description", "medium", WEIGHTS["meta_description"],
                "The meta description is injected by JavaScript.",
                rendered.meta_description[:160]))

    if rendered.canonical and not raw.canonical:
        add(Gap("canonical", "high", WEIGHTS["canonical"],
                "The canonical link only exists after rendering.",
                rendered.canonical))
    elif rendered.canonical and raw.canonical and rendered.canonical != raw.canonical:
        add(Gap("canonical", "high", WEIGHTS["canonical"],
                "The canonical URL changes after rendering.",
                f"raw: {raw.canonical} / rendered: {rendered.canonical}"))

    if rendered.h1 and not raw.h1:
        add(Gap("h1", "critical", WEIGHTS["h1"],
                "There is no H1 in the served HTML; the browser adds it.",
                f"Rendered H1: {rendered.h1[0]!r}"))

    missing_headings = _missing_items(raw.headings, rendered.headings)
    if missing_headings:
        share = len(missing_headings) / max(1, len(rendered.headings))
        add(Gap("headings", "high" if share > 0.4 else "medium",
                WEIGHTS["headings"] * min(1.0, share),
                f"{len(missing_headings)} of {len(rendered.headings)} "
                f"{'heading is' if len(missing_headings) == 1 else 'headings are'} "
                "missing from the served HTML.",
                " | ".join(missing_headings[:5])))

    missing_pct = report.missing_word_pct
    if missing_pct >= 5:
        sev = "critical" if missing_pct >= 50 else "high" if missing_pct >= 20 else "medium"
        add(Gap("body_text", sev, WEIGHTS["body_text"] * min(1.0, missing_pct / 100),
                f"{missing_pct:.0f}% of the body text is only there after JavaScript.",
                f"{report.raw_words} words served, {report.rendered_words} words rendered."))

    missing_paras = _missing_items(raw.paragraphs, rendered.paragraphs)
    if missing_paras:
        share = len(missing_paras) / max(1, len(rendered.paragraphs))
        add(Gap("paragraphs", "high" if share > 0.4 else "medium",
                WEIGHTS["paragraphs"] * min(1.0, share),
                f"{len(missing_paras)} of {len(rendered.paragraphs)} content "
                f"{'block is' if len(missing_paras) == 1 else 'blocks are'} client-side only.",
                _first_answerish(missing_paras)))

    missing_types = [t for t in rendered.jsonld_types if t not in raw.jsonld_types]
    if missing_types:
        add(Gap("jsonld", "high", WEIGHTS["jsonld"],
                "Structured data is added by JavaScript: "
                + ", ".join(missing_types),
                "Rich results and AI answers read the served HTML."))

    missing_links = [l for l in rendered.links if l not in set(raw.links)]
    if missing_links:
        share = len(missing_links) / max(1, len(rendered.links))
        add(Gap("links", "medium" if share < 0.5 else "high",
                WEIGHTS["links"] * min(1.0, share),
                f"{len(missing_links)} internal "
                f"{'link is' if len(missing_links) == 1 else 'links are'} "
                "only in the rendered DOM.",
                " | ".join(missing_links[:5])))

    return report


def _first_answerish(paragraphs: list[str]) -> str:
    """Point at the paragraph an AI engine would most likely have quoted."""
    best = max(paragraphs, key=lambda p: _answer_fit(p), default="")
    return best[:220]


def _answer_fit(paragraph: str) -> float:
    n = len(words(paragraph))
    if n == 0:
        return 0.0
    # 40-60 words is the length engines lift verbatim.
    return 1.0 - min(1.0, abs(50 - n) / 50)
