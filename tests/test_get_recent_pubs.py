"""Regression tests for dsn-ranking.py::get_recent_pubs — counts how many
of an author's publications fall within the RECENT year window, including
the disambiguation-suffix fallback (e.g. dblp keys like '...21a')."""


def test_counts_only_pubs_within_the_recent_window(dsn_ranking):
    dsn_ranking.RECENT = 2022
    pubs = {
        "conf/dsn/AuthorX23",  # 2023 -> recent
        "conf/dsn/AuthorY21",  # 2021 -> not recent
        "conf/ftcs/AuthorZ95",  # 1995 -> not recent
    }
    assert dsn_ranking.get_recent_pubs(pubs) == 1


def test_handles_disambiguation_letter_suffix(dsn_ranking):
    dsn_ranking.RECENT = 2020
    pubs = {"conf/dsn/CayreGANKM21a"}  # letter suffix -> should resolve to 2021
    assert dsn_ranking.get_recent_pubs(pubs) == 1


def test_maps_two_digit_year_to_the_correct_century(dsn_ranking):
    dsn_ranking.RECENT = 1999
    pubs = {"conf/ftcs/FooB99"}  # '99' -> 1999, not 2099
    assert dsn_ranking.get_recent_pubs(pubs) == 1


def test_returns_zero_for_empty_pub_set(dsn_ranking):
    dsn_ranking.RECENT = 2022
    assert dsn_ranking.get_recent_pubs(set()) == 0
