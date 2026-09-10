from rendergap.diff import compare
from rendergap.extract import extract


def test_a_client_rendered_page_loses_almost_everything(spa):
    fields = {g.field for g in spa.gaps}
    assert {"title", "h1", "body_text", "jsonld", "canonical"} <= fields
    assert spa.missing_word_pct > 90
    assert spa.score <= 30


def test_a_server_rendered_page_has_no_gap(ssr):
    assert ssr.gaps == []
    assert ssr.score == 100


def test_a_cookie_banner_added_by_javascript_is_not_a_gap(ssr):
    # The rendered fixture adds a cookie banner; it is outside <main>, so it
    # must not be reported as missing content.
    assert all(g.field != "body_text" for g in ssr.gaps)


def test_partial_hydration_reports_only_what_is_missing(hybrid):
    fields = {g.field for g in hybrid.gaps}
    assert "title" not in fields
    assert "h1" not in fields
    assert {"headings", "meta_description", "jsonld", "paragraphs"} <= fields
    assert 20 < hybrid.score < 95


def test_content_only_in_the_raw_html_is_never_a_gap():
    raw = extract("<html><body><main><p>A sentence that is only in the served HTML.</p></main></body></html>")
    rendered = extract("<html><body><main></main></body></html>")
    assert compare(raw, rendered).gaps == []


def test_a_changed_title_is_flagged_but_less_harshly_than_a_missing_one():
    raw_missing = extract("<html><head></head><body></body></html>")
    raw_changed = extract("<html><head><title>Old title entirely different</title></head><body></body></html>")
    rendered = extract("<html><head><title>New page title</title></head><body></body></html>")
    missing = compare(raw_missing, rendered).gaps[0]
    changed = compare(raw_changed, rendered).gaps[0]
    assert missing.severity == "critical"
    assert changed.severity == "high"
    assert changed.points < missing.points


def test_a_canonical_that_changes_after_rendering_is_flagged():
    raw = extract('<html><head><link rel="canonical" href="/a"></head><body></body></html>', "https://e.com/x")
    rendered = extract('<html><head><link rel="canonical" href="/b"></head><body></body></html>', "https://e.com/x")
    gap = next(g for g in compare(raw, rendered).gaps if g.field == "canonical")
    assert "changes" in gap.summary


def test_the_detail_points_at_the_most_quotable_missing_paragraph(hybrid):
    gap = next(g for g in hybrid.gaps if g.field == "paragraphs")
    assert "hiatal hernia" in gap.detail


def test_score_is_bounded_and_gaps_are_sorted_by_severity(spa):
    assert 0 <= spa.score <= 100
    order = [g.severity for g in spa.sorted_gaps()]
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    assert order == sorted(order, key=lambda s: rank[s])


def test_whitespace_only_differences_do_not_create_a_gap():
    raw = extract("<html><body><main><p>One    two three four five six seven.</p></main></body></html>")
    rendered = extract("<html><body><main><p>One two three\nfour five six seven.</p></main></body></html>")
    assert compare(raw, rendered).gaps == []


def test_counts_of_one_are_written_in_the_singular(hybrid):
    links = next(g for g in hybrid.gaps if g.field == "links")
    headings = next(g for g in hybrid.gaps if g.field == "headings")
    assert "1 internal link is" in links.summary
    assert "1 of 2 heading is missing" in headings.summary
