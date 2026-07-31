"""Regression tests for dsn-ranking.py::update_authors and persist_authors —
the in-memory tally and its JSON serialization."""
import json


def test_update_authors_creates_new_entry(dsn_ranking):
    dsn_ranking.authorList = {}
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe23")

    assert dsn_ranking.authorList["00/1"]["name"] == "Jane Doe"
    assert dsn_ranking.authorList["00/1"]["pubs"] == {"conf/dsn/Doe23"}


def test_update_authors_accumulates_pubs_for_existing_author(dsn_ranking):
    dsn_ranking.authorList = {}
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe23")
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe24")

    assert dsn_ranking.authorList["00/1"]["pubs"] == {
        "conf/dsn/Doe23",
        "conf/dsn/Doe24",
    }


def test_update_authors_deduplicates_the_same_pub_key(dsn_ranking):
    dsn_ranking.authorList = {}
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe23")
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe23")

    assert dsn_ranking.authorList["00/1"]["pubs"] == {"conf/dsn/Doe23"}


def test_update_authors_keeps_distinct_authors_separate(dsn_ranking):
    dsn_ranking.authorList = {}
    dsn_ranking.update_authors("00/1", "Jane Doe", "conf/dsn/Doe23")
    dsn_ranking.update_authors("00/2", "John Roe", "conf/dsn/Doe23")

    assert set(dsn_ranking.authorList.keys()) == {"00/1", "00/2"}


def test_persist_authors_round_trips_through_json(tmp_path, dsn_ranking):
    authors = {
        "00/1": {"name": "Jane Doe", "pubs": {"conf/dsn/Doe23", "conf/dsn/Doe24"}}
    }
    out_file = tmp_path / "authorlist.json"

    dsn_ranking.persist_authors(authors, str(out_file))

    saved = json.loads(out_file.read_text())
    assert saved["00/1"]["pid"] == "00/1"
    assert sorted(saved["00/1"]["pubs"]) == ["conf/dsn/Doe23", "conf/dsn/Doe24"]
