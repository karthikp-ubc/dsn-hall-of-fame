"""Regression tests for dsn-ranking.py::get_authors — the per-year driver
that calls dblp.search_pub, filters hits, and tallies authors. dblp.search_pub
itself is mocked here (its pagination behaviour is covered separately in
test_bug2_pagination.py) so these tests isolate get_authors' own logic."""
import json

from helpers import make_hit

QUERY = "conf/dsn/2023"


def test_counts_solo_and_coauthored_papers_and_skips_workshop_papers(
    monkeypatch, dsn_ranking
):
    dsn_ranking.authorList = {}
    body = {
        "result": {
            "hits": {
                "hit": [
                    make_hit(1, solo_author=True),
                    make_hit(2, solo_author=False),
                    make_hit(3, venue="DSN-W"),  # workshop -> filtered out
                ]
            }
        }
    }
    monkeypatch.setattr(dsn_ranking.dblp, "search_pub", lambda venue: json.dumps(body))

    papers = dsn_ranking.get_authors(QUERY)

    assert papers == 2
    assert len(dsn_ranking.authorList) == 3  # author1, author2, coauthor2
    assert dsn_ranking.authorList["00/2"]["pubs"] == {"conf/dsn/Author223"}
    assert dsn_ranking.authorList["01/2"]["pubs"] == {"conf/dsn/Author223"}


def test_returns_zero_when_year_has_no_hits(monkeypatch, dsn_ranking):
    dsn_ranking.authorList = {}
    body = {"result": {"hits": {}}}
    monkeypatch.setattr(dsn_ranking.dblp, "search_pub", lambda venue: json.dumps(body))

    assert dsn_ranking.get_authors(QUERY) == 0
    assert dsn_ranking.authorList == {}


def test_returns_zero_on_malformed_response_instead_of_crashing(
    monkeypatch, dsn_ranking
):
    monkeypatch.setattr(dsn_ranking.dblp, "search_pub", lambda venue: "not json")

    assert dsn_ranking.get_authors(QUERY) == 0


def test_returns_zero_when_search_pub_signals_failure_with_none(
    monkeypatch, dsn_ranking
):
    """Once bug 1 is fixed, search_pub returns None after exhausting
    retries; get_authors must treat that as "no data" rather than crash."""
    monkeypatch.setattr(dsn_ranking.dblp, "search_pub", lambda venue: None)

    assert dsn_ranking.get_authors(QUERY) == 0
