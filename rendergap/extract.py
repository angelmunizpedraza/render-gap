"""Turn an HTML document into the handful of things a search or AI crawler cares about."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

# Chrome and everything else drop these before reading the page.
NON_CONTENT_TAGS = ("script", "style", "template", "noscript", "svg")

# Repeated on every page: useful for navigation, useless as an answer.
BOILERPLATE_TAGS = ("nav", "header", "footer", "aside")

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _text_of(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


@dataclass
class Snapshot:
    """What one HTML document offers a crawler."""

    url: str = ""
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    robots: str = ""
    h1: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    images_with_alt: int = 0
    images_total: int = 0
    jsonld_types: list[str] = field(default_factory=list)
    jsonld_raw: list[dict[str, Any]] = field(default_factory=list)
    body_text: str = ""

    @property
    def word_count(self) -> int:
        return len(words(self.body_text))

    @property
    def indexable(self) -> bool:
        return "noindex" not in self.robots.lower()


def _jsonld(soup: BeautifulSoup) -> tuple[list[str], list[dict]]:
    types: list[str] = []
    blocks: list[dict] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            for node in (graph if isinstance(graph, list) else [item]):
                if not isinstance(node, dict):
                    continue
                blocks.append(node)
                t = node.get("@type")
                if isinstance(t, list):
                    types.extend(str(x) for x in t)
                elif t:
                    types.append(str(t))
    return sorted(set(types)), blocks


def extract(html: str, url: str = "") -> Snapshot:
    """Parse one HTML document into a Snapshot.

    The same function is used for the raw response and for the rendered DOM, so
    any difference in the result is a difference in the documents, never in the
    parsing.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    types, blocks = _jsonld(soup)

    for tag in soup.find_all(NON_CONTENT_TAGS):
        tag.decompose()

    title_tag = soup.find("title")
    title = _text_of(title_tag) if title_tag else ""

    def meta(name: str, attr: str = "name") -> str:
        tag = soup.find("meta", attrs={attr: re.compile(rf"^{name}$", re.I)})
        return (tag.get("content") or "").strip() if tag else ""

    canonical_tag = soup.find("link", attrs={"rel": re.compile("^canonical$", re.I)})
    canonical = (canonical_tag.get("href") or "").strip() if canonical_tag else ""
    if canonical and url:
        canonical = urldefrag(urljoin(url, canonical))[0]

    h1 = [_text_of(t) for t in soup.find_all("h1") if _text_of(t)]
    headings = [_text_of(t) for t in soup.find_all(["h1", "h2", "h3"]) if _text_of(t)]

    main = soup.find("main") or soup.find("article") or soup.body or soup
    body = BeautifulSoup(str(main), "html.parser")
    for tag in body.find_all(BOILERPLATE_TAGS):
        tag.decompose()

    paragraphs = [_text_of(p) for p in body.find_all(["p", "li"]) if len(words(_text_of(p))) >= 5]

    links: list[str] = []
    for a in body.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        target = urldefrag(urljoin(url, href))[0] if url else href
        if url and urlparse(target).netloc != urlparse(url).netloc:
            continue
        links.append(target)

    images = soup.find_all("img")

    return Snapshot(
        url=url,
        title=title,
        meta_description=meta("description"),
        canonical=canonical,
        robots=meta("robots"),
        h1=h1,
        headings=headings,
        paragraphs=paragraphs,
        links=sorted(set(links)),
        images_with_alt=sum(1 for i in images if (i.get("alt") or "").strip()),
        images_total=len(images),
        jsonld_types=types,
        jsonld_raw=blocks,
        body_text=_text_of(body),
    )
