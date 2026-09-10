import json

from rendergap.report import csv_report, json_report, markdown_report


def test_markdown_has_a_summary_table_and_a_section_per_page(spa, ssr):
    md = markdown_report([spa, ssr])
    assert md.startswith("# render-gap")
    assert "| Page | Score |" in md
    assert md.count("## ") == 2
    assert "No gap found" in md


def test_pipes_in_content_do_not_break_the_table(hybrid):
    hybrid.gaps[0].summary = "a | b | c"
    for line in markdown_report([hybrid]).splitlines():
        if line.startswith("| ") and "---" not in line and "Page |" not in line:
            assert line.count("|") - line.count("\\|") in (3, 4, 5, 6, 7), line


def test_json_report_round_trips(spa):
    data = json.loads(json_report([spa]))
    assert data[0]["score"] == spa.score
    assert data[0]["gaps"]


def test_csv_has_one_row_per_gap_plus_a_row_for_clean_pages(spa, ssr):
    rows = csv_report([spa, ssr]).strip().splitlines()
    assert rows[0].startswith("url,score,verdict")
    assert len(rows) == 1 + len(spa.gaps) + 1
    assert "no gap" in rows[-1]


def test_pipes_are_escaped_in_tables_but_left_alone_in_bullets(hybrid):
    hybrid.url = "Page A | Page B"
    md = markdown_report([hybrid])
    table_row = next(l for l in md.splitlines() if l.startswith("| Page A"))
    assert "Page A \\| Page B" in table_row
    heading = next(l for l in md.splitlines() if l.startswith("## "))
    assert "Page A | Page B" in heading
