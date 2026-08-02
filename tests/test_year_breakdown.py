"""Regression tests for dsn-ranking.py::get_pub_year and ::get_year_breakdown —
the per-year publication counts that feed the website's year-range filter,
trend graph, and author-comparison graph (added alongside those features)."""


def test_get_pub_year_two_digit_key(dsn_ranking):
    assert dsn_ranking.get_pub_year("conf/dsn/ArlatKL88") == 1988
    assert dsn_ranking.get_pub_year("conf/dsn/AuthorX23") == 2023


def test_get_pub_year_handles_disambiguation_letter_suffix(dsn_ranking):
    assert dsn_ranking.get_pub_year("conf/dsn/CayreGANKM21a") == 2021


def test_get_pub_year_maps_two_digit_year_to_the_correct_century(dsn_ranking):
    # '>50' -> 1900s, '<=50' -> 2000s (matches the pre-existing get_recent_pubs rule).
    assert dsn_ranking.get_pub_year("conf/ftcs/FooB99") == 1999
    assert dsn_ranking.get_pub_year("conf/dsn/FooB05") == 2005


def test_get_pub_year_handles_three_digit_suffix_seen_in_newer_dblp_keys(dsn_ranking):
    # dblp occasionally emits a leading disambiguation digit before the year
    # (e.g. "...025" for 2025); the last two digits still carry the year.
    assert dsn_ranking.get_pub_year("conf/dsn/LiaoAMBK025") == 2025


def test_get_year_breakdown_counts_publications_per_year(dsn_ranking):
    pubs = [
        "conf/ftcs/ArlatKL88",
        "conf/dsn/AuthorX23",
        "conf/dsn/AuthorY23",
        "conf/dsn/AuthorZ21a",
    ]
    assert dsn_ranking.get_year_breakdown(pubs) == {
        "1988": 1,
        "2023": 2,
        "2021": 1,
    }


def test_get_year_breakdown_omits_years_with_zero_publications(dsn_ranking):
    breakdown = dsn_ranking.get_year_breakdown(["conf/dsn/AuthorX23"])
    assert "2022" not in breakdown
    assert breakdown == {"2023": 1}


def test_get_year_breakdown_empty_pubs_returns_empty_dict(dsn_ranking):
    assert dsn_ranking.get_year_breakdown([]) == {}


def test_get_year_breakdown_sums_match_get_recent_pubs_and_total(dsn_ranking):
    # Sanity check that the two derived views of the same pub list agree:
    # sum(years.values()) == len(pubs), and the recent-window subset of
    # get_year_breakdown's keys matches get_recent_pubs's count.
    dsn_ranking.RECENT = 2022
    pubs = {"conf/dsn/AuthorX23", "conf/dsn/AuthorY21", "conf/ftcs/AuthorZ95"}
    breakdown = dsn_ranking.get_year_breakdown(pubs)
    assert sum(breakdown.values()) == len(pubs)
    recent_from_breakdown = sum(c for y, c in breakdown.items() if int(y) >= dsn_ranking.RECENT)
    assert recent_from_breakdown == dsn_ranking.get_recent_pubs(pubs)
