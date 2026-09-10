from rendergap.score import NON_JS_CITATION_BOTS, score_report


def test_verdict_labels_match_the_score(spa, ssr, hybrid):
    assert score_report(ssr)["verdict"] == "clean"
    assert score_report(spa)["verdict"] in {"invisible", "degraded"}
    assert score_report(hybrid)["verdict"] in {"minor", "degraded"}


def test_report_is_json_serialisable_and_complete(hybrid):
    s = score_report(hybrid)
    assert set(s) == {
        "url", "score", "verdict", "message", "raw_words",
        "rendered_words", "missing_word_pct", "gaps", "affects",
    }
    assert all(set(g) == {"field", "severity", "points", "summary", "detail"} for g in s["gaps"])


def test_the_affected_crawlers_are_named(ssr):
    assert "OAI-SearchBot" in score_report(ssr)["affects"]
    assert "PerplexityBot" in NON_JS_CITATION_BOTS
