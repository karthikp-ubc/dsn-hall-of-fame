# What's changed

A high-level summary of recent changes to the DSN Hall of Fame site and crawler:

1. **Fixed reliability bugs in the DBLP crawler.** It was silently undercounting papers in recent, high-volume years (DBLP paginates its results and the crawler wasn't handling that), and a bug in its retry logic could crash the whole run on a single transient network hiccup. Both are fixed, so re-crawls are now complete and don't need to be restarted by hand.

2. **Made re-running the ranking much cheaper.** The crawler now checkpoints each author's raw publication data, so if we only need to tweak how the ranking is computed (not re-fetch from DBLP), we can regenerate it in seconds instead of the hours a full crawl takes under DBLP's rate limits.

3. **Modernized the website.** Visitors can now filter the ranking to any year range, sort by any column, search by name or affiliation, compare several authors' publication trends on a graph, drill into one author's full history, and export the current view as a spreadsheet.

4. **Closed a security gap.** The old page inserted DBLP-sourced text directly into the page's HTML, a known class of web vulnerability — that's fixed as part of the website rewrite.

5. **Added an automated test suite.** There were previously no tests at all; now both the crawler and the website have one, so future changes can be checked automatically instead of by hand.

6. **Removed unrelated leftover code.** An old, unused tool for a different conference's hall of fame (and the dead code it left behind) had been sitting in the repo since the DSN version was first forked from it — cleaned that out to reduce clutter for whoever touches this next.
