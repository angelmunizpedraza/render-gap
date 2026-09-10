from pathlib import Path

from rendergap import cli


def _args(fixtures_dir, kind, *extra):
    return ["diff", str(fixtures_dir / f"{kind}_raw.html"),
            str(fixtures_dir / f"{kind}_rendered.html"), *extra]


def test_diff_writes_every_output(tmp_path, fixtures_dir):
    md, js, cs = tmp_path / "r.md", tmp_path / "r.json", tmp_path / "r.csv"
    code = cli.main(_args(fixtures_dir, "spa", "--url", "https://example.com/boas-surgery",
                          "--md", str(md), "--json", str(js), "--csv", str(cs)))
    assert code == 0
    assert md.read_text(encoding="utf-8").startswith("# render-gap")
    assert '"verdict"' in js.read_text(encoding="utf-8")
    assert cs.read_text(encoding="utf-8").startswith("url,score,verdict")


def test_report_is_printed_when_no_output_path_is_given(capsys, fixtures_dir):
    assert cli.main(_args(fixtures_dir, "ssr")) == 0
    assert "render-gap" in capsys.readouterr().out


def test_min_score_gate_fails_on_a_client_rendered_page(tmp_path, capsys, fixtures_dir):
    code = cli.main(_args(fixtures_dir, "spa", "--min-score", "80", "--md", str(tmp_path / "x.md")))
    assert code == 1
    assert "below the --min-score gate" in capsys.readouterr().err


def test_min_score_gate_passes_on_a_server_rendered_page(tmp_path, fixtures_dir):
    assert cli.main(_args(fixtures_dir, "ssr", "--min-score", "90", "--md", str(tmp_path / "x.md"))) == 0


def test_max_missing_pct_gate(tmp_path, capsys, fixtures_dir):
    code = cli.main(_args(fixtures_dir, "spa", "--max-missing-pct", "10", "--md", str(tmp_path / "x.md")))
    assert code == 1
    assert "--max-missing-pct gate" in capsys.readouterr().err


def test_missing_file_exits_two(capsys, fixtures_dir):
    try:
        cli.main(["diff", "/nope/raw.html", str(fixtures_dir / "ssr_rendered.html")])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")
    assert "file not found" in capsys.readouterr().err


def test_run_without_a_browser_reports_it_cleanly(monkeypatch, capsys):
    from rendergap import fetch

    monkeypatch.setattr(cli, "fetch_raw", lambda *a, **k: "<html></html>")

    def boom(*a, **k):
        raise fetch.BrowserUnavailable("Rendering needs a browser.")

    monkeypatch.setattr(cli, "fetch_rendered", boom)
    assert cli.main(["run", "https://example.com/"]) == 2
    assert "needs a browser" in capsys.readouterr().err


def test_run_uses_both_fetchers_and_scores_the_pair(monkeypatch, capsys, fixtures_dir):
    monkeypatch.setattr(cli, "fetch_raw",
                        lambda *a, **k: (fixtures_dir / "spa_raw.html").read_text(encoding="utf-8"))
    monkeypatch.setattr(cli, "fetch_rendered",
                        lambda *a, **k: (fixtures_dir / "spa_rendered.html").read_text(encoding="utf-8"))
    assert cli.main(["run", "https://example.com/boas-surgery"]) == 0
    assert "invisible" in capsys.readouterr().out
