"""Shared dblp-key-to-publication-year helpers.

Used by both dsn-ranking.py (the crawler) and backfill_years.py (the no-network
re-derivation script). Kept in its own normally-importable module rather than
inside dsn-ranking.py, since dsn-ranking.py's hyphenated filename can't be
`import`ed directly (see tests/conftest.py's _load_dsn_ranking for that workaround,
which only dsn-ranking.py itself still needs).
"""


def get_pub_year(key):
    """Extract the publication year from a dblp key (e.g. `conf/dsn/ArlatKL88` -> 1988).
    Args:
        key: dblp publication key.

    Returns:
        The 4-digit publication year as an int.
    """
    try:
        yyy = int(key[len(key) - 2:])
    except ValueError:
        yyy = int(key[len(key) - 3:len(key) - 1])
    return yyy + 1900 if yyy > 50 else yyy + 2000


def get_year_breakdown(pubs):
    """Compute the number of publications per year for an author.
    Args:
        pubs: List of publications for the author.

    Returns:
        A dict mapping year (as string) to publication count, omitting years with 0 publications.
    """
    counts = {}
    for key in pubs:
        year = str(get_pub_year(key))
        counts[year] = counts.get(year, 0) + 1
    return counts
