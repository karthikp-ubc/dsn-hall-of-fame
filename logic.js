/**
 * DOM-free logic for the DSN Hall of Fame front-end: filtering, ranking, sorting,
 * and color assignment. Kept separate from app.js so it can be loaded both by the
 * browser (<script src="logic.js">, exposes window.DSNLogic) and by Node's built-in
 * test runner (require('./logic.js')), with no build step either way.
 */
(function (global) {
	'use strict';

	const ENTITY_MAP = {
		'&amp;': '&',
		'&lt;': '<',
		'&gt;': '>',
		'&quot;': '"',
		'&#39;': "'",
		'&apos;': "'",
		'&nbsp;': ' ',
	};

	function decodeEntities(str) {
		return String(str).replace(/&(?:amp|lt|gt|quot|#39|apos|nbsp);/g, (m) => ENTITY_MAP[m]);
	}

	function papersInRange(entry, from, to) {
		let sum = 0;
		const years = entry.years || {};
		for (let y = from; y <= to; y++) {
			sum += years[String(y)] || 0;
		}
		return sum;
	}

	// Returns {min, max}, falling back to `fallback` ({min, max}) when `data` has no year info.
	function computeYearBounds(data, fallback) {
		let min = null;
		let max = null;
		for (const entry of data) {
			for (const y of Object.keys(entry.years || {})) {
				const n = parseInt(y, 10);
				if (min === null || n < min) min = n;
				if (max === null || n > max) max = n;
			}
		}
		return {
			min: min === null ? fallback.min : min,
			max: max === null ? fallback.max : max,
		};
	}

	// Assigns standard competition ranking (1,2,2,4,...) by `papers` descending, mutating each row's `.rank`.
	function computeRanks(rows) {
		const byPapersDesc = [...rows].sort((a, b) => b.papers - a.papers);
		let rank = 1;
		let last = null;
		byPapersDesc.forEach((r, i) => {
			if (last !== null && r.papers !== last) rank = i + 1;
			r.rank = rank;
			last = r.papers;
		});
		return rows;
	}

	// Maps allData -> rows scoped to [fromYear, toYear], dropping authors with 0 papers in range,
	// and annotating each row with a `.rank` recomputed for that range (plus the original
	// all-time `.rank`/`.total` preserved as `.allTimeRank`/`.allTimeTotal`).
	function getFilteredRows(allData, fromYear, toYear) {
		const rows = allData
			.map((e) => ({ ...e, papers: papersInRange(e, fromYear, toYear), allTimeRank: e.rank, allTimeTotal: e.total }))
			.filter((r) => r.papers > 0);
		computeRanks(rows);
		return rows;
	}

	// Sorts `rows` in place by `sortKey` ('rank' | 'papers' | 'author' | 'affiliation') and returns it.
	function sortRows(rows, sortKey, sortDir) {
		const mul = sortDir === 'asc' ? 1 : -1;
		rows.sort((a, b) => {
			let av, bv;
			switch (sortKey) {
				case 'papers':
					av = a.papers; bv = b.papers; break;
				case 'author':
					av = a.author.toLowerCase(); bv = b.author.toLowerCase(); break;
				case 'affiliation':
					av = (a.affiliation || '').toLowerCase(); bv = (b.affiliation || '').toLowerCase(); break;
				case 'rank':
				default:
					av = a.rank; bv = b.rank; break;
			}
			if (av < bv) return -1 * mul;
			if (av > bv) return 1 * mul;
			return 0;
		});
		return rows;
	}

	// Case-insensitive substring match against author name or affiliation (both entity-decoded,
	// so searching "&" matches an affiliation stored as "Reliable &amp; High..."). Does not
	// touch `.rank` — rank stays scoped to the full year-range standings, not the search results.
	function filterBySearch(rows, query) {
		const q = decodeEntities(String(query || '')).trim().toLowerCase();
		if (!q) return rows;
		return rows.filter((r) => {
			const author = decodeEntities(r.author || '').toLowerCase();
			const affiliation = decodeEntities(r.affiliation || '').toLowerCase();
			return author.includes(q) || affiliation.includes(q);
		});
	}

	function yearRangeArray(fromYear, toYear) {
		const years = [];
		for (let y = fromYear; y <= toYear; y++) years.push(y);
		return years;
	}

	// Top N author names by `.papers` descending (stable: ties keep `rows`' relative order),
	// matching what the "Top 5 / Top 10" quick-select buttons plot.
	function topNByPapers(rows, n) {
		return [...rows]
			.sort((a, b) => b.papers - a.papers)
			.slice(0, n)
			.map((r) => r.author);
	}

	// Stateful color assignment: the first-seen order for each distinct name determines its
	// palette slot, and that assignment is stable for the assigner's lifetime — so a name's
	// color never changes when the surrounding selection changes (see dataviz skill: "color
	// follows the entity, never its rank").
	function createColorAssigner(palette) {
		const assignments = new Map();
		return function colorFor(name) {
			if (!assignments.has(name)) {
				assignments.set(name, palette[assignments.size % palette.length]);
			}
			return assignments.get(name);
		};
	}

	const DSNLogic = {
		decodeEntities,
		papersInRange,
		computeYearBounds,
		computeRanks,
		getFilteredRows,
		sortRows,
		filterBySearch,
		yearRangeArray,
		topNByPapers,
		createColorAssigner,
	};

	if (typeof module !== 'undefined' && module.exports) {
		module.exports = DSNLogic;
	} else {
		global.DSNLogic = DSNLogic;
	}
})(typeof window !== 'undefined' ? window : globalThis);
