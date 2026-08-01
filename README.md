# DSN Hall of Fame — website

A static leaderboard of DSN/FTCS conference authors by publication count, with
year-range filtering, sortable columns, a publications-per-year graph, a
multi-author comparison view, and a per-author profile.

For the Python crawler that produces the underlying data, see [README.rst](README.rst).
For architectural notes aimed at future contributors (human or AI), see
[CLAUDE.md](CLAUDE.md).

## Running it locally

There's no build step. Serve the repo root with any static file server and open
`dsn-hof.html`:

```bash
python3 -m http.server 8080
# then open http://localhost:8080/dsn-hof.html
```

Opening `dsn-hof.html` directly via `file://` also mostly works, but some
browsers restrict `fetch()` for local files — a local server is more reliable.

## Features

- **Year-range filter** — a From/To year picker plus "All time / Last 5 years /
  Last 10 years" presets. Narrowing the range recomputes each author's paper
  count and rank for that range (with ties handled via standard competition
  ranking: 1, 2, 2, 4, ...).
- **Sortable table** — click any column header (Rank / Name / Papers /
  Affiliation) to sort; click again to reverse.
- **Graph, with two modes:**
  - *Trend* — total papers per year across all authors in the current range.
  - *Compare* — up to 8 individually chosen authors' papers-per-year, overlaid.
    Select authors via the checkbox column, or use the "Top 5" / "Top 10"
    quick-select buttons (based on papers in the current year range). A
    selected author keeps their line color even as the selection changes.
- **Author profile** — click any author's name to open their full publication
  history (all-time, independent of the current year-range filter) as a bar
  chart, alongside their all-time and in-range rank/paper count.

## Data

The site reads `ranking.json`, an array of author records:

```json
{
  "author": "Karthik Pattabiraman",
  "total": 24,
  "rank": 4,
  "recent": 7,
  "affiliation": "University of British Columbia, Vancouver, Canada",
  "years": { "2014": 3, "2018": 2, "2025": 3, "...": "..." }
}
```

`total`/`rank` are all-time figures from the original crawl; `years` is a sparse
per-year publication count used for everything range-dependent.

### Regenerating the data

- **Full re-crawl** (new DSN/FTCS proceedings, new authors, refreshed
  affiliations): `python3 dsn-ranking.py`. This queries DBLP directly, is rate
  limited, and takes a while — see `README.rst` for details.
- **Just refreshing the per-year breakdown** (e.g. after changing how years are
  derived from DBLP keys) without re-crawling: `python3 backfill_years.py`. This
  re-derives `ranking.json`'s `years` field from the already-crawled
  `authorlist.json`, with no network calls.

## Testing

```bash
pytest -q                          # crawler / data pipeline (Python)
node --test tests/js/logic.test.js # front-end filtering/ranking/sorting logic (JS)
```

Both should pass before shipping a change to either the data pipeline or the
front-end's `logic.js`. UI-only changes in `app.js` (DOM rendering, Chart.js
wiring) aren't covered by automated tests — verify those manually in a browser.
