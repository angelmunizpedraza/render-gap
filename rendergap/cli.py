"""render-gap command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .diff import GapReport, compare
from .extract import extract
from .fetch import BrowserUnavailable, fetch_raw, fetch_rendered
from .report import csv_report, json_report, markdown_report
from .score import score_report

EXIT_OK = 0
EXIT_GATE = 1
EXIT_INPUT = 2


def _pair_from_files(raw_path: str, rendered_path: str, url: str) -> GapReport:
    for p in (raw_path, rendered_path):
        if not Path(p).is_file():
            print(f"render-gap: file not found: {p}", file=sys.stderr)
            raise SystemExit(EXIT_INPUT)
    raw = extract(Path(raw_path).read_text(encoding="utf-8"), url)
    rendered = extract(Path(rendered_path).read_text(encoding="utf-8"), url)
    return compare(raw, rendered, url)


def _pair_from_url(url: str, timeout: int, settle_ms: int) -> GapReport:
    raw_html = fetch_raw(url, timeout=timeout)
    rendered_html = fetch_rendered(url, timeout=timeout, settle_ms=settle_ms)
    return compare(extract(raw_html, url), extract(rendered_html, url), url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="render-gap",
        description="Show what your page gives a browser and hides from a non-JavaScript crawler.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="analyse one or more URLs")
    run.add_argument("urls", nargs="+", help="URLs to analyse")
    run.add_argument("--timeout", type=int, default=20)
    run.add_argument("--settle-ms", type=int, default=1500,
                     help="extra wait after networkidle before reading the DOM")
    run.add_argument("--md", help="write the Markdown report here")
    run.add_argument("--json", dest="json_path", help="write the JSON report here")
    run.add_argument("--csv", dest="csv_path", help="write the CSV report here")
    run.add_argument("--min-score", type=int, default=None,
                     help="exit 1 if any page scores below this")
    run.add_argument("--max-missing-pct", type=float, default=None,
                     help="exit 1 if any page hides more than this share of its body text")

    diff = sub.add_parser("diff", help="compare two local HTML files (no browser needed)")
    diff.add_argument("raw", help="the HTML your server returns")
    diff.add_argument("rendered", help="the DOM after JavaScript")
    diff.add_argument("--url", default="", help="URL these files came from, for link resolution")
    diff.add_argument("--md")
    diff.add_argument("--json", dest="json_path")
    diff.add_argument("--csv", dest="csv_path")
    diff.add_argument("--min-score", type=int, default=None)
    diff.add_argument("--max-missing-pct", type=float, default=None)

    return p


def _emit(reports: list[GapReport], args) -> None:
    wrote = False
    if getattr(args, "md", None):
        Path(args.md).write_text(markdown_report(reports), encoding="utf-8")
        wrote = True
    if getattr(args, "json_path", None):
        Path(args.json_path).write_text(json_report(reports), encoding="utf-8")
        wrote = True
    if getattr(args, "csv_path", None):
        Path(args.csv_path).write_text(csv_report(reports), encoding="utf-8")
        wrote = True
    if not wrote:
        print(markdown_report(reports))


def _gate(reports: list[GapReport], args) -> int:
    failed = False
    for r in reports:
        s = score_report(r)
        if args.min_score is not None and s["score"] < args.min_score:
            print(f"render-gap: {s['url']} scores {s['score']}, below the "
                  f"--min-score gate of {args.min_score}", file=sys.stderr)
            failed = True
        if args.max_missing_pct is not None and s["missing_word_pct"] > args.max_missing_pct:
            print(f"render-gap: {s['url']} hides {s['missing_word_pct']}% of its body text, "
                  f"above the --max-missing-pct gate of {args.max_missing_pct}", file=sys.stderr)
            failed = True
    return EXIT_GATE if failed else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "diff":
        reports = [_pair_from_files(args.raw, args.rendered, args.url)]
    else:
        reports = []
        for url in args.urls:
            try:
                reports.append(_pair_from_url(url, args.timeout, args.settle_ms))
            except BrowserUnavailable as exc:
                print(f"render-gap: {exc}", file=sys.stderr)
                return EXIT_INPUT
            except Exception as exc:  # network, DNS, HTTP status
                print(f"render-gap: could not analyse {url}: {exc}", file=sys.stderr)
                return EXIT_INPUT

    _emit(reports, args)
    return _gate(reports, args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
