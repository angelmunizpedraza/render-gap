"""Get the two versions of a page: what the server sends, and what a browser builds.

The raw fetch only needs `requests`. The rendered fetch needs a browser, which
is an optional extra (`pip install "render-gap[browser]"`) so that the analysis
and the whole test suite run without one.
"""

from __future__ import annotations

import time

import requests

# Identify honestly, and identify as the thing we are simulating.
RAW_UA = (
    "render-gap/0.1 (+https://github.com/angelmunizpedraza/render-gap) "
    "simulating a non-JavaScript citation crawler"
)

DEFAULT_TIMEOUT = 20


class BrowserUnavailable(RuntimeError):
    """Raised when a rendered snapshot is requested and Playwright is not installed."""


def fetch_raw(url: str, timeout: int = DEFAULT_TIMEOUT, session: requests.Session | None = None) -> str:
    """Exactly what a crawler that does not run JavaScript receives."""
    s = session or requests.Session()
    response = s.get(url, timeout=timeout, headers={"User-Agent": RAW_UA})
    response.raise_for_status()
    return response.text


def fetch_rendered(url: str, timeout: int = DEFAULT_TIMEOUT, settle_ms: int = 1500) -> str:
    """The DOM after the page's JavaScript has run.

    `settle_ms` is a deliberate extra wait after networkidle: a lot of content
    is injected by a framework one tick after the last request finishes, and
    without the wait the tool would under-report the gap.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise BrowserUnavailable(
            'Rendering needs a browser. Install with: pip install "render-gap[browser]" '
            "&& playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            time.sleep(settle_ms / 1000)
            return page.content()
        finally:
            browser.close()
