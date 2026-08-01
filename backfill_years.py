"""One-off script: add a per-year publication breakdown to an existing ranking.json,
derived from authorlist.json. No DBLP calls needed since authorlist.json already has
every author's publication keys.
"""
import json

from importlib.machinery import SourceFileLoader

dsn_ranking = SourceFileLoader('dsn_ranking', './dsn-ranking.py').load_module()


def merge_years(ranking, authorlist, get_year_breakdown):
    """Add a 'years' breakdown to each ranking entry, matched to authorlist by name.

    Args:
        ranking: list of ranking.json entries; mutated in place.
        authorlist: authorlist.json dict (pid -> {'name', 'pubs', ...}).
        get_year_breakdown: function(pubs) -> {year: count}, e.g. dsn_ranking.get_year_breakdown.

    Returns:
        List of ranking['author'] values that had no matching authorlist entry.
    """
    by_name = {a['name']: a for a in authorlist.values()}

    missing = []
    for entry in ranking:
        author = by_name.get(entry['author'])
        if author is None:
            missing.append(entry['author'])
            continue
        entry['years'] = get_year_breakdown(author['pubs'])

    return missing


def main():
    with open('ranking.json', encoding='utf-8') as f:
        ranking = json.load(f)

    with open('authorlist.json', encoding='utf-8') as f:
        authorlist = json.load(f)

    missing = merge_years(ranking, authorlist, dsn_ranking.get_year_breakdown)

    if missing:
        print(f"Warning: {len(missing)} ranking entries had no authorlist match: {missing}")

    with open('ranking.json', 'w', encoding='utf-8') as f:
        json.dump(ranking, f, indent=4)

    print(f"Backfilled 'years' for {len(ranking) - len(missing)} authors.")


if __name__ == '__main__':
    main()
