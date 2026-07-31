"""Regression tests for dblp.search().

Like search_pub before it was fixed, search() used a hand-rolled retry
loop per request. It didn't have the search_pub variable-name typo, but
it shared the same underlying flaw: if every retry failed, the `resp`
(or `resp1`) variable was never assigned, so the function would crash
with an UnboundLocalError instead of returning gracefully. It's now
built on the same _get_with_retries() helper as search_pub, returning
an empty list instead of crashing when a request can't be completed.
"""
import dblp

from helpers import FakeResponse

AUTHOR_SEARCH_XML = """<?xml version="1.0"?>
<authors>
  <author urlpt="99/1">Jane Doe</author>
</authors>
"""

PERSON_XML_NO_HOMONYM = """<?xml version="1.0"?>
<dblpperson name="Jane Doe"></dblpperson>
"""

PERSON_XML_WITH_HOMONYM = """<?xml version="1.0"?>
<dblpperson name="Jane Doe">
  <homonym>88/2</homonym>
  <homonym>88/3</homonym>
</dblpperson>
"""


def _get_dispatch(by_url):
    """Fake requests.get that returns a canned response keyed by URL prefix."""

    def _get(url, params=None, **kwargs):
        for prefix, response in by_url.items():
            if url.startswith(prefix):
                return response
        raise AssertionError(f"unexpected URL requested: {url}")

    return _get


def test_search_returns_one_author_per_urlpt_on_success(monkeypatch):
    monkeypatch.setattr(
        dblp.requests,
        "get",
        _get_dispatch(
            {
                dblp.DBLP_AUTHOR_SEARCH_URL: FakeResponse(text=AUTHOR_SEARCH_XML),
                dblp.DBLP_PERSON_URL.split("{")[0]: FakeResponse(
                    text=PERSON_XML_NO_HOMONYM
                ),
            }
        ),
    )

    authors = dblp.search("jane doe")

    assert len(authors) == 1
    assert authors[0].urlpt == "99/1"


def test_search_expands_homonyms_into_separate_authors(monkeypatch):
    monkeypatch.setattr(
        dblp.requests,
        "get",
        _get_dispatch(
            {
                dblp.DBLP_AUTHOR_SEARCH_URL: FakeResponse(text=AUTHOR_SEARCH_XML),
                dblp.DBLP_PERSON_URL.split("{")[0]: FakeResponse(
                    text=PERSON_XML_WITH_HOMONYM
                ),
            }
        ),
    )

    authors = dblp.search("jane doe")

    assert sorted(a.urlpt for a in authors) == ["88/2", "88/3"]


def test_search_retries_after_one_transient_failure(monkeypatch):
    calls = {"n": 0}

    def flaky_get(url, params=None, **kwargs):
        if url.startswith(dblp.DBLP_AUTHOR_SEARCH_URL):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("simulated transient network failure")
            return FakeResponse(text=AUTHOR_SEARCH_XML)
        return FakeResponse(text=PERSON_XML_NO_HOMONYM)

    monkeypatch.setattr(dblp.requests, "get", flaky_get)

    authors = dblp.search("jane doe")

    assert len(authors) == 1
    assert calls["n"] == 2


def test_search_returns_empty_list_when_author_search_exhausts_retries(monkeypatch):
    def always_fail(*args, **kwargs):
        raise ConnectionError("simulated persistent network failure")

    monkeypatch.setattr(dblp.requests, "get", always_fail)

    result = dblp.search("jane doe")

    assert result == []


def test_search_skips_urlpt_when_person_lookup_exhausts_retries(monkeypatch):
    """One author's person-page lookup fails entirely; search() should
    skip that author rather than crash the whole call."""

    def _get(url, params=None, **kwargs):
        if url.startswith(dblp.DBLP_AUTHOR_SEARCH_URL):
            return FakeResponse(text=AUTHOR_SEARCH_XML)
        raise ConnectionError("simulated persistent network failure")

    monkeypatch.setattr(dblp.requests, "get", _get)

    result = dblp.search("jane doe")

    assert result == []


def test_search_returns_empty_list_on_malformed_author_search_xml(monkeypatch):
    monkeypatch.setattr(
        dblp.requests, "get", lambda *a, **k: FakeResponse(text="not xml")
    )

    result = dblp.search("jane doe")

    assert result == []
