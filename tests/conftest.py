from pathlib import Path

import pytest

from rendergap.diff import compare
from rendergap.extract import extract

FIX = Path(__file__).parent / "fixtures"

URLS = {
    "spa": "https://example.com/boas-surgery",
    "ssr": "https://example.com/cherry-eye",
    "hybrid": "https://example.com/endoscopy",
}


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def _report(kind: str):
    url = URLS[kind]
    raw = extract(_read(f"{kind}_raw.html"), url)
    rendered = extract(_read(f"{kind}_rendered.html"), url)
    return compare(raw, rendered, url)


@pytest.fixture()
def spa():
    return _report("spa")


@pytest.fixture()
def ssr():
    return _report("ssr")


@pytest.fixture()
def hybrid():
    return _report("hybrid")


@pytest.fixture()
def fixtures_dir():
    return FIX
