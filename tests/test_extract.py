from rendergap.extract import extract


def test_scripts_and_styles_never_count_as_content():
    html = (
        "<html><body><main><p>Real sentence with enough words to count here.</p>"
        "<script>var hidden='this text is not content at all';</script>"
        "<style>.x{color:red}</style></main></body></html>"
    )
    page = extract(html)
    assert "hidden" not in page.body_text
    assert "color" not in page.body_text


def test_nav_and_footer_are_excluded_from_the_body_text():
    html = (
        "<html><body><nav>Home Contact About Us Careers</nav>"
        "<main><p>The paragraph that actually answers the question goes here.</p></main>"
        "<footer>Terms and privacy and cookie policy</footer></body></html>"
    )
    page = extract(html)
    assert "Careers" not in page.body_text
    assert "privacy" not in page.body_text
    assert "answers the question" in page.body_text


def test_jsonld_types_are_read_including_graph_nodes():
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@graph":[{"@type":"Organization"},{"@type":["FAQPage","WebPage"]}]}'
        "</script></head><body></body></html>"
    )
    page = extract(html)
    assert page.jsonld_types == ["FAQPage", "Organization", "WebPage"]


def test_invalid_jsonld_is_ignored_rather_than_crashing():
    html = '<html><head><script type="application/ld+json">{not json,,}</script></head><body></body></html>'
    assert extract(html).jsonld_types == []


def test_links_are_resolved_and_offsite_links_dropped():
    html = (
        '<html><body><main><a href="/a">a</a><a href="https://other.com/b">b</a>'
        '<a href="#top">top</a><a href="mailto:x@y.z">mail</a></main></body></html>'
    )
    page = extract(html, "https://example.com/here")
    assert page.links == ["https://example.com/a"]


def test_canonical_is_absolutised():
    html = '<html><head><link rel="canonical" href="/canonical-here"></head><body></body></html>'
    assert extract(html, "https://example.com/x").canonical == "https://example.com/canonical-here"


def test_noindex_is_detected():
    html = '<html><head><meta name="robots" content="NOINDEX, follow"></head><body></body></html>'
    page = extract(html)
    assert page.indexable is False


def test_short_list_items_do_not_count_as_content_blocks():
    html = "<html><body><main><ul><li>Home</li><li>Blog</li></ul></main></body></html>"
    assert extract(html).paragraphs == []
