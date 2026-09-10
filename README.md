# render-gap

**Your page looks complete in a browser. Now look at it the way an AI crawler does.**
`render-gap` fetches the HTML your server actually returns, renders the same URL in a real browser, and reports exactly which headings, paragraphs, links and structured data only exist after JavaScript has run.

[![CI](https://github.com/angelmunizpedraza/render-gap/actions/workflows/ci.yml/badge.svg)](https://github.com/angelmunizpedraza/render-gap/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Why this exists

Googlebot renders JavaScript. The crawlers that decide whether an AI answer can cite you mostly do not:

`OAI-SearchBot` · `ChatGPT-User` · `PerplexityBot` · `Claude-SearchBot` · `Claude-User` · `Google-Extended` · `Applebot-Extended` · `CCBot`

So a page can rank perfectly well and still be invisible to every engine that writes answers. The failure is silent: you open the URL, you see your content, everything looks fine. The crawler received an empty `<div id="root">`.

That is the single most common finding in the GEO audits I run, and it is the one people argue with the most, because the page *looks* right. This tool ends the argument with a number.

## What it reports

| Check | Why it matters |
|---|---|
| `title` | Missing or rewritten by JS — the crawler indexes the empty one. |
| `meta_description` | Injected client-side, so snippets fall back to guesswork. |
| `canonical` | Absent or *different* after rendering: two different signals for the same URL. |
| `h1` | No H1 in the served HTML at all. |
| `headings` | Which H2/H3 the crawler never sees — these are the question-shaped ones engines match against prompts. |
| `body_text` | What share of the copy is client-side only, in words. |
| `paragraphs` | Which content blocks are missing, and it points at **the most quotable one** (closest to the 40–60 words engines lift verbatim). |
| `jsonld` | Structured data added by JavaScript: `FAQPage`, `Product`, `Article`… |
| `links` | Internal links that only exist after hydration, so the link graph the crawler builds is smaller than yours. |

Each gap carries a severity and a point cost, and the page ends with a score out of 100:

```
100  ── clean       a non-JS crawler sees what a human sees
 90  ── minor       most of the page is served
 70  ── degraded    a meaningful part does not exist for the crawler
 40  ── invisible   to a non-JS crawler this page is mostly empty
```

## The part most tools get wrong

Two things make the difference between a useful report and a noisy one:

**1. Only missing content counts.** Content that exists in the raw HTML and gets replaced or removed by the framework is not a crawler problem, so it is never reported. A cookie banner or a chat widget that JavaScript adds is not content either: boilerplate (`nav`, `header`, `footer`, `aside`) is excluded from the body comparison on both sides. That is why a properly server-rendered page scores exactly 100 instead of "98, because of a cookie bar".

**2. The wait matters.** Frameworks routinely inject the important paragraph one tick *after* the last network request finishes. Reading the DOM at `networkidle` under-reports the gap, so `render-gap` waits an extra `--settle-ms` (1500 ms by default) before taking the snapshot.

## Install

```bash
pip install -e .                  # analysis only
pip install -e ".[browser]"       # + rendering
playwright install chromium
```

The browser is an **optional extra** on purpose. The `diff` subcommand compares two HTML files you already have, needs no browser at all, and is what runs in CI.

## Use

Analyse live URLs:

```bash
render-gap run https://example.com/pricing https://example.com/blog/post \
  --md report.md --json report.json
```

Compare two files you captured yourself — no browser required:

```bash
render-gap diff served.html rendered.html --url https://example.com/pricing
```

Gate a deploy:

```bash
render-gap diff served.html rendered.html --min-score 80
render-gap run https://example.com/ --max-missing-pct 10
```

Exit codes: `0` pass · `1` a gate failed · `2` bad input (missing file, no browser, unreachable URL).

## Use it as a GitHub Action

Add this to a workflow and your build fails the day a deploy starts hiding
content behind JavaScript. The action installs render-gap and Chromium,
checks the URLs you give it, writes a Markdown report and appends it to the
job summary.

```yaml
name: Render gap
on:
  push:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"

jobs:
  render-gap:
    runs-on: ubuntu-latest
    steps:
      - uses: angelmunizpedraza/render-gap@v1
        with:
          urls: |
            https://example.com/
            https://example.com/pricing
          min-score: "80"
```

| Input | Default | What it does |
|---|---|---|
| `urls` | — | URLs to check, separated by spaces or newlines. Required. |
| `min-score` | `80` | Fail if any URL scores below this. Empty string reports without gating. |
| `max-missing-pct` | *(none)* | Fail if more than this percentage of the body text is missing from the served HTML. |
| `settle-ms` | `1500` | Wait after `networkidle` before reading the DOM. Raise it for frameworks that hydrate late. |
| `markdown` | `render-gap-report.md` | Where to write the Markdown report. |
| `json` | *(none)* | Where to write the JSON report. |
| `job-summary` | `true` | Append the Markdown report to the GitHub job summary. |
| `python-version` | `3.12` | Python used to run render-gap. |
| `ref` | *(default branch)* | Git ref of render-gap to install. |

The action runs against `https://example.com/` in this repository's own CI, so
it is tested on every push rather than only documented.

## What the output looks like

```
| Page                             | Score  | Verdict   | Served words | Rendered words | Missing |
|----------------------------------|-------:|-----------|-------------:|---------------:|--------:|
| https://example.com/boas-surgery |  0/100 | invisible |            0 |            139 |  100.0% |

## https://example.com/boas-surgery — 0/100 (invisible)

- 🔴 body_text  — 100% of the body text is only there after JavaScript.
                    0 words served, 139 words rendered.
- 🔴 h1         — There is no H1 in the served HTML; the browser adds it.
- 🔴 title      — The <title> is written by JavaScript.
- 🟠 paragraphs — 3 of 3 content blocks are client-side only.
                    Most bulldogs breathe noticeably better within forty-eight hours…
- 🟠 jsonld     — Structured data is added by JavaScript: FAQPage
```

`examples/client-rendered.html` is a deliberately broken page you can point the tool at to see this for yourself.

## Method notes, and what this tool does not claim

- **Headless Chromium is not GPTBot.** It is a good stand-in for "what exists after JS", not proof of what any specific engine stores. The tool tells you what a non-JS client is missing; it does not promise a citation.
- **Similarity, not equality.** Strings are matched at 92% similarity, so a re-wrapped line or a normalised quote mark is not reported as missing content.
- **Word counts exclude boilerplate** on both sides, so the percentage is about the article, not the chrome around it.
- **Nothing is scored by an LLM.** Same inputs, same output, every run. That is what makes it safe to put in CI.

## Project layout

```
rendergap/
  extract.py   HTML → the handful of things a crawler cares about
  diff.py      raw vs rendered, weighted gaps and the score
  score.py     verdict, affected crawlers, serialisable report
  fetch.py     requests for raw, Playwright (optional) for rendered
  report.py    Markdown, JSON, CSV
  cli.py       render-gap run / render-gap diff, with CI gates
tests/         35 tests, no network and no browser required
```

## Related tools

Part of a set of open-source tools I use on client work — all Python, MIT, deterministic, no API keys:

[geo-check](https://github.com/angelmunizpedraza/geo-check) · [citeable](https://github.com/angelmunizpedraza/citeable) · [serp-to-ai-diff](https://github.com/angelmunizpedraza/serp-to-ai-diff) · [ai-visibility-tracker](https://github.com/angelmunizpedraza/ai-visibility-tracker) · [linkjuice](https://github.com/angelmunizpedraza/linkjuice) · [llms-txt-generator](https://github.com/angelmunizpedraza/llms-txt-generator) · [seo-audit](https://github.com/angelmunizpedraza/seo-audit) · [ga4-report](https://github.com/angelmunizpedraza/ga4-report)

`geo-check` tells you whether the crawlers are allowed in. `render-gap` tells you whether there was anything there when they arrived. `citeable` tells you whether it was worth quoting.

## Licence

MIT — Ángel Muñiz Pedraza · [LinkedIn](https://www.linkedin.com/in/angel-muniz-seo) · angelhd029@gmail.com
