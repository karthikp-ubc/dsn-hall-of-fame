"""Regression tests for dsn-ranking.py::filter_papers — the logic that
decides whether a dblp hit counts as a real main-track paper (as opposed
to a workshop paper, abstract, keynote, or editorial front-matter)."""
from helpers import make_hit

QUERY = "conf/dsn/2023"


def test_keeps_full_length_main_track_paper(dsn_ranking):
    info = make_hit(1)["info"]
    assert dsn_ranking.filter_papers(info, QUERY) is True


def test_rejects_workshop_track_by_venue(dsn_ranking):
    info = make_hit(1, venue="DSN-W")["info"]
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_rejects_supplemental_volume_by_venue(dsn_ranking):
    info = make_hit(1, venue="DSN-S")["info"]
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_rejects_short_abstract_by_page_count(dsn_ranking):
    info = make_hit(1, pages="45-47")["info"]  # 3 pages, below MIN_PAGES=4
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_rejects_single_page_entry(dsn_ranking):
    info = make_hit(1, pages="45")["info"]  # no '-' -> treated as 1 page
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_rejects_entry_with_missing_pages_field(dsn_ranking):
    info = make_hit(1)["info"]
    del info["pages"]
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_keeps_paper_with_unparsable_page_range(dsn_ranking):
    # int('12:1') fails -> except path treats it as a long (kept) paper
    info = make_hit(1, pages="12:1-12:20")["info"]
    assert dsn_ranking.filter_papers(info, QUERY) is True


def test_keeps_paper_with_isbn_prefixed_doi_format(dsn_ranking):
    info = make_hit(1)["info"]
    info["doi"] = "10.1109/DSN58367.2023.00013"  # ISBN digits between DSN and year
    assert dsn_ranking.filter_papers(info, QUERY) is True


def test_rejects_doi_for_the_wrong_year(dsn_ranking):
    info = make_hit(1, year=2023)["info"]
    info["doi"] = "10.1109/DSN.2022.00013"  # doesn't match the 2023 query year
    assert dsn_ranking.filter_papers(info, QUERY) is False


def test_keeps_paper_missing_doi_field(dsn_ranking):
    # Documents current (debatable) behaviour: a KeyError on pub["doi"]
    # is treated as "can't verify, so keep it" rather than "reject it".
    info = make_hit(1)["info"]
    del info["doi"]
    assert dsn_ranking.filter_papers(info, QUERY) is True
