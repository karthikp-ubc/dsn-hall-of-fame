# Changes since bagchi/dsn-hall-of-fame

*(Everything on this branch that isn't in the public repo at
[github.com/bagchi/dsn-hall-of-fame](https://github.com/bagchi/dsn-hall-of-fame),
whose `master` is at `132fe72` "Fix some bugs" — 16 commits plus uncommitted
work on top.)*

## 1. DBLP client hardening (`dblp/__init__.py`)

- **Fixed a crash-causing typo:** `search_pub`'s hand-rolled retry loop had a
  variable-name typo (`timeOutCount3` vs `timeoutCount3`) that turned *any*
  transient network failure into an unhandled `UnboundLocalError`, crashing the
  whole crawl — costly since `get_authors()` calls it outside any try/except
  and progress only checkpoints once per year.
- **Fixed silent undercounting:** `search_pub` requested `h=1000` assuming one
  response held everything, but DBLP caps each response at 100 hits regardless
  of `h`. Confirmed live that `conf/dsn/2023` has 154 entries and only 30 of 49
  real papers made the first page — recent, popular years were being silently
  undercounted. Now pages through DBLP's offset parameter until every hit is
  collected.
- **Consolidated three duplicated retry loops** (`search_pub`, `search`,
  `get_affiliation`, each with its own ad-hoc counter) into one shared
  `_get_with_retries()` helper — rate-limit-aware (backs off with a growing
  delay on HTTP 429/5xx, unlike ordinary failures) and fails gracefully
  instead of crashing once retries are exhausted.
- **Added 403 handling** for DBLP's soft-ban response.
- **Removed dead code:** once nothing called `dblp.search()` any more (see §6),
  its supporting `Author`/`Publication` classes, their shared lazy-loading base
  class, an unused namedtuple, and ~260 lines of related XML-parsing code had
  zero remaining callers and were deleted — along with a second, already-
  superseded `__get_affiliation` implementation (old retry pattern, dead since
  an earlier rewrite, never called by anything).

## 2. Crawl/ranking pipeline

- **`authorlist.json` checkpoint:** raw per-author publication keys are now
  saved separately from `ranking.json`, so the ranking can be regenerated
  without re-running the full, slow, rate-limited DBLP crawl.
- **Per-year publication breakdown:** added a `years` field (via a new shared
  `pub_years.py` module: `get_pub_year` + `get_year_breakdown`) so the site can
  filter/graph by *any* year range instead of one fixed "recent" window.
- **`backfill_years.py`:** re-derives that `years` breakdown from
  already-crawled `authorlist.json` data with **zero new DBLP requests** — for
  when only the breakdown logic changes, not the underlying paper counts.
- Updated the ranking to include 2026 and re-crawled with the fixes above.

## 3. Front-end: full rewrite

The old `load.js` built the table via manual DOM/`innerHTML` calls with no
filtering, sorting, or graphing. Replaced with a `logic.js` / `app.js` split:

- **`logic.js`** — pure, DOM-free filtering/ranking/sorting/CSV/search logic,
  loadable by both the browser (`window.DSNLogic`) and Node (so it's
  unit-testable without a DOM library). **`app.js`** — a thin
  rendering/event-wiring layer over it.
- **New features:** a year-range filter (with All-time/Last-5/Last-10 presets)
  that recomputes each author's rank for that range; click-to-sort table
  columns; a live name/affiliation search; a Trend/Compare graph (Chart.js,
  colorblind-safe validated palette) with checkbox + Top-5/Top-10 multi-author
  comparison, capped at 8 plotted series; a per-author profile modal (all-time
  history, independent of the active filter); and CSV export of exactly what's
  currently on screen.
- **Fixed a latent injection-shaped pattern along the way, not as the goal:**
  the old `load.js` wrote DBLP-sourced affiliation text via `innerHTML`
  (`c5.innerHTML = ... .concat(data[i].affiliation)`); the rewrite renders
  everything via `textContent` with explicit HTML-entity decoding.

## 4. Testing

Nonexistent before this branch:

- First pytest suite, added alongside the retry/pagination fix — regression
  tests that are verified to fail against the pre-fix code, plus general
  coverage for `filter_papers`, `get_recent_pubs`, author bookkeeping, and
  `get_authors`/`get_affiliation`/`search` parsing.
- Extended with tests for the year-breakdown/backfill logic and for
  `_get_with_retries` directly (the 429-backoff sequence itself, not just its
  callers).
- First JS test suite (Node's built-in test runner) for `logic.js`, at ~99%
  line coverage.

## 5. Documentation

- **`README.md`** (new) — site-focused: how to run it locally, feature
  overview, data format, how to regenerate `ranking.json` two ways, test
  commands. The original `README.rst` only ever documented the Python crawler.
- **`CLAUDE.md`** (new) — architecture and rationale notes for whoever works on
  this next: the `logic.js`/`app.js` split, why colors are sourced from CSS
  custom properties rather than duplicated in JS, a browser-caching gotcha hit
  during development, and known data-quality quirks.

## 6. Removed as dead weight

- **`isca.py` / `isca-parallel.py` / `ISCA-README.rst`** — the unrelated ISCA
  Hall of Fame tool this repo was originally forked from. Verified first: zero
  callers of/dependents on anything DSN-specific in either direction (the only
  string matches for "isca" elsewhere were false positives — "d**isca**rd",
  "P**isca**taway, NJ").
- **`dblp`'s `search()`/`Author`/`Publication` subsystem** — only reachable via
  the ISCA scripts above; dead once they were removed (§1).
