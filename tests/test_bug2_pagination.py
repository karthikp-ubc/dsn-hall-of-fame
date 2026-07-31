"""Regression tests for the dblp.search_pub pagination bug.

dblp's /search/publ/api endpoint hard-caps each response at 100 hits
*regardless of the requested `h` value*; the remainder has to be fetched
with the `f` (first-result offset) parameter. search_pub requests
h=1000 and returns a single page, so any conference-year whose combined
dblp listing (main track + workshops + supplemental volume, all indexed
under the same conf/dsn/YYYY key) exceeds 100 entries is silently
undercounted. Verified live against dblp: conf/dsn/2023 has @total=154,
and 19 of the 49 real DSN main-track papers for that year only appear
on page 2.
"""
import json

import dblp

from helpers import FakeResponse, make_hit


def _paged_get(pages):
    """Fake requests.get serving `pages` keyed by the requested `f` offset."""

    def _get(url, params=None, **kwargs):
        first = int((params or {}).get("f", 0))
        return pages[first]

    return _get


def test_search_pub_returns_all_hits_when_under_the_page_cap(monkeypatch):
    hits = [make_hit(i) for i in range(5)]
    body = {
        "result": {
            "hits": {
                "@total": "5",
                "@computed": "5",
                "@sent": "5",
                "@first": "0",
                "hit": hits,
            }
        }
    }
    monkeypatch.setattr(
        dblp.requests, "get", _paged_get({0: FakeResponse(json_data=body)})
    )

    result = json.loads(dblp.search_pub("conf/dsn/2001"))

    assert len(result["result"]["hits"]["hit"]) == 5


def test_search_pub_aggregates_pages_past_the_100_hit_cap(monkeypatch):
    """Mirrors the real conf/dsn/2023 shape: 154 total hits split as
    100 + 54 across two pages."""
    page1_hits = [make_hit(i) for i in range(100)]
    page2_hits = [make_hit(i) for i in range(100, 154)]

    page1 = {
        "result": {
            "hits": {
                "@total": "154",
                "@computed": "100",
                "@sent": "100",
                "@first": "0",
                "hit": page1_hits,
            }
        }
    }
    page2 = {
        "result": {
            "hits": {
                "@total": "154",
                "@computed": "154",
                "@sent": "54",
                "@first": "100",
                "hit": page2_hits,
            }
        }
    }
    monkeypatch.setattr(
        dblp.requests,
        "get",
        _paged_get({0: FakeResponse(json_data=page1), 100: FakeResponse(json_data=page2)}),
    )

    result = json.loads(dblp.search_pub("conf/dsn/2023"))

    returned_keys = {h["info"]["key"] for h in result["result"]["hits"]["hit"]}
    assert len(returned_keys) == 154, (
        f"expected all 154 dblp entries to be aggregated across pages, got "
        f"{len(returned_keys)} — search_pub is not paginating past dblp's "
        f"100-hit-per-request cap"
    )


def test_search_pub_handles_year_with_zero_hits(monkeypatch):
    body = {"result": {"hits": {"@total": "0", "@computed": "0", "@sent": "0"}}}
    monkeypatch.setattr(
        dblp.requests, "get", _paged_get({0: FakeResponse(json_data=body)})
    )

    result = json.loads(dblp.search_pub("conf/dsn/1975"))

    assert "hit" not in result["result"]["hits"]


def test_get_authors_counts_papers_from_every_page(monkeypatch, dsn_ranking):
    """End-to-end: once search_pub aggregates all pages, get_authors should
    count DSN main-track papers from both pages, not just the first 100
    raw hits."""
    dsn_ranking.authorList = {}

    page1_hits = [make_hit(i, pages="10-20") for i in range(100)]
    page2_hits = [make_hit(i, pages="10-20") for i in range(100, 130)]
    page1 = {
        "result": {
            "hits": {
                "@total": "130",
                "@sent": "100",
                "@first": "0",
                "hit": page1_hits,
            }
        }
    }
    page2 = {
        "result": {
            "hits": {
                "@total": "130",
                "@sent": "30",
                "@first": "100",
                "hit": page2_hits,
            }
        }
    }
    monkeypatch.setattr(
        dblp.requests,
        "get",
        _paged_get({0: FakeResponse(json_data=page1), 100: FakeResponse(json_data=page2)}),
    )

    papers = dsn_ranking.get_authors("conf/dsn/2023")

    assert papers == 130
