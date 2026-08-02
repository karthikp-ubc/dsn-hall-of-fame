"""Regression tests for backfill_years.py::merge_years — matches ranking.json
entries to authorlist.json entries by author name and attaches a per-year
publication breakdown, without needing to re-crawl DBLP."""

import backfill_years


def test_merge_years_attaches_breakdown_for_matching_authors():
    ranking = [{"author": "Alice A.", "total": 2}]
    authorlist = {"1/1": {"name": "Alice A.", "pubs": ["conf/dsn/AuthorX23", "conf/dsn/AuthorY23"]}}

    missing = backfill_years.merge_years(ranking, authorlist, lambda pubs: {"2023": len(pubs)})

    assert missing == []
    assert ranking[0]["years"] == {"2023": 2}


def test_merge_years_reports_authors_with_no_authorlist_match():
    ranking = [{"author": "Alice A."}, {"author": "Ghost Author"}]
    authorlist = {"1/1": {"name": "Alice A.", "pubs": []}}

    missing = backfill_years.merge_years(ranking, authorlist, lambda pubs: {})

    assert missing == ["Ghost Author"]
    assert "years" in ranking[0]
    assert "years" not in ranking[1]


def test_merge_years_matches_by_name_regardless_of_authorlist_key_order():
    ranking = [{"author": "Bob B."}, {"author": "Alice A."}]
    authorlist = {
        "2/2": {"name": "Alice A.", "pubs": ["conf/dsn/X20"]},
        "1/1": {"name": "Bob B.", "pubs": ["conf/dsn/Y21", "conf/dsn/Z21"]},
    }

    backfill_years.merge_years(ranking, authorlist, lambda pubs: {"n": len(pubs)})

    assert ranking[0]["years"] == {"n": 2}  # Bob
    assert ranking[1]["years"] == {"n": 1}  # Alice


def test_merge_years_end_to_end_with_real_get_year_breakdown(dsn_ranking):
    ranking = [{"author": "Alice A."}]
    authorlist = {
        "1/1": {
            "name": "Alice A.",
            "pubs": ["conf/ftcs/ArlatKL88", "conf/dsn/AuthorX23", "conf/dsn/AuthorY23"],
        }
    }

    missing = backfill_years.merge_years(ranking, authorlist, dsn_ranking.get_year_breakdown)

    assert missing == []
    assert ranking[0]["years"] == {"1988": 1, "2023": 2}
