'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
	decodeEntities,
	papersInRange,
	computeYearBounds,
	computeRanks,
	getFilteredRows,
	sortRows,
	filterBySearch,
	yearRangeArray,
	topNByPapers,
	buildCSV,
	createColorAssigner,
} = require('../../logic.js');

function sampleData() {
	// Mirrors the shape of ranking.json entries.
	return [
		{ author: 'Alice A.', affiliation: 'Uni A', total: 5, rank: 1, years: { '2020': 2, '2021': 3 } },
		{ author: 'Bob B.', affiliation: 'Uni B', total: 5, rank: 1, years: { '2019': 1, '2020': 4 } },
		{ author: 'Carol C.', affiliation: 'Uni C', total: 3, rank: 3, years: { '2020': 3 } },
		{ author: 'Dave D.', affiliation: '', total: 1, rank: 4, years: { '1988': 1 } },
	];
}

test('decodeEntities decodes common HTML entities without touching plain text', () => {
	assert.equal(decodeEntities('Reliable &amp; High Performance'), 'Reliable & High Performance');
	assert.equal(decodeEntities('&lt;tag&gt; &quot;q&quot; &#39;s&#39;'), '<tag> "q" \'s\'');
	assert.equal(decodeEntities('Plain text'), 'Plain text');
});

test('papersInRange sums only years within [from, to], treating missing years as 0', () => {
	const entry = { years: { '2019': 1, '2020': 4, '2021': 2 } };
	assert.equal(papersInRange(entry, 2019, 2021), 7);
	assert.equal(papersInRange(entry, 2020, 2020), 4);
	assert.equal(papersInRange(entry, 2022, 2025), 0);
});

test('papersInRange treats a missing years object as no publications', () => {
	assert.equal(papersInRange({}, 1988, 2026), 0);
});

test('computeYearBounds finds the min/max year across all entries', () => {
	const bounds = computeYearBounds(sampleData(), { min: 1900, max: 1900 });
	assert.deepEqual(bounds, { min: 1988, max: 2021 });
});

test('computeYearBounds falls back when no entry has year data', () => {
	const bounds = computeYearBounds([{ years: {} }, {}], { min: 1988, max: 2026 });
	assert.deepEqual(bounds, { min: 1988, max: 2026 });
});

test('computeRanks assigns standard competition ranking (ties share a rank, next rank skips)', () => {
	const rows = [{ papers: 5 }, { papers: 5 }, { papers: 3 }, { papers: 1 }];
	computeRanks(rows);
	assert.deepEqual(rows.map((r) => r.rank), [1, 1, 3, 4]);
});

test('computeRanks handles all-tied and all-distinct cases', () => {
	const allTied = [{ papers: 2 }, { papers: 2 }, { papers: 2 }];
	computeRanks(allTied);
	assert.deepEqual(allTied.map((r) => r.rank), [1, 1, 1]);

	const distinct = [{ papers: 3 }, { papers: 2 }, { papers: 1 }];
	computeRanks(distinct);
	assert.deepEqual(distinct.map((r) => r.rank), [1, 2, 3]);
});

test('getFilteredRows drops authors with 0 papers in range and recomputes rank for that range', () => {
	// Narrow the range to just 2020: Alice=2, Bob=4, Carol=3, Dave=0 (dropped).
	const rows = getFilteredRows(sampleData(), 2020, 2020);
	assert.deepEqual(
		rows.map((r) => r.author).sort(),
		['Alice A.', 'Bob B.', 'Carol C.']
	);
	const bob = rows.find((r) => r.author === 'Bob B.');
	assert.equal(bob.papers, 4);
	assert.equal(bob.rank, 1); // highest in this range
	// All-time fields are preserved alongside the range-scoped ones.
	assert.equal(bob.allTimeRank, 1);
	assert.equal(bob.allTimeTotal, 5);
});

test('getFilteredRows over the full range reproduces the original all-time totals', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	assert.equal(rows.length, 4);
	const alice = rows.find((r) => r.author === 'Alice A.');
	assert.equal(alice.papers, alice.allTimeTotal);
});

test('sortRows sorts numerically by papers/rank and case-insensitively by text fields', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);

	sortRows(rows, 'papers', 'desc');
	assert.deepEqual(rows.map((r) => r.papers), [5, 5, 3, 1]);

	sortRows(rows, 'author', 'asc');
	assert.deepEqual(rows.map((r) => r.author), ['Alice A.', 'Bob B.', 'Carol C.', 'Dave D.']);

	sortRows(rows, 'affiliation', 'asc');
	// Dave has an empty affiliation, so it sorts first ascending.
	assert.equal(rows[0].author, 'Dave D.');
});

test('sortRows sorts by rank (and falls back to rank for an unrecognized key)', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026); // Alice & Bob tie at rank 1, Carol 3, Dave 4

	sortRows(rows, 'rank', 'desc');
	assert.deepEqual(rows.map((r) => r.author), ['Dave D.', 'Carol C.', 'Alice A.', 'Bob B.']);

	sortRows(rows, 'rank', 'asc');
	assert.deepEqual(rows.map((r) => r.rank), [1, 1, 3, 4]);

	sortRows(rows, 'not-a-real-sort-key', 'desc');
	assert.deepEqual(rows.map((r) => r.author), ['Dave D.', 'Carol C.', 'Alice A.', 'Bob B.']);
});

test('yearRangeArray produces an inclusive sequence', () => {
	assert.deepEqual(yearRangeArray(2020, 2020), [2020]);
	assert.deepEqual(yearRangeArray(2018, 2021), [2018, 2019, 2020, 2021]);
});

test('topNByPapers returns the top N author names by papers, descending', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	const top2 = topNByPapers(rows, 2);
	assert.equal(top2.length, 2);
	assert.ok(top2.includes('Alice A.'));
	assert.ok(top2.includes('Bob B.'));
});

test('topNByPapers clamps to the available rows when N exceeds the row count', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	assert.equal(topNByPapers(rows, 100).length, 4);
});

test('createColorAssigner assigns colors from the palette in first-seen order and reuses them stably', () => {
	const colorFor = createColorAssigner(['red', 'green', 'blue']);
	assert.equal(colorFor('A'), 'red');
	assert.equal(colorFor('B'), 'green');
	assert.equal(colorFor('A'), 'red'); // stable on repeat lookups
	assert.equal(colorFor('C'), 'blue');
	assert.equal(colorFor('D'), 'red'); // cycles past the palette end
});

test('createColorAssigner never changes an existing name\'s color when new names are seen', () => {
	const colorFor = createColorAssigner(['red', 'green', 'blue']);
	colorFor('A');
	const before = colorFor('A');
	colorFor('B');
	colorFor('C');
	colorFor('D');
	assert.equal(colorFor('A'), before);
});

test('filterBySearch matches by author name, case-insensitively', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	const matches = filterBySearch(rows, 'alice');
	assert.deepEqual(matches.map((r) => r.author), ['Alice A.']);
});

test('filterBySearch matches by affiliation as well as name', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	const matches = filterBySearch(rows, 'uni b');
	assert.deepEqual(matches.map((r) => r.author), ['Bob B.']);
});

test('filterBySearch decodes HTML entities before matching', () => {
	const rows = [{ author: 'X', affiliation: 'Reliable &amp; High Performance', papers: 1 }];
	assert.equal(filterBySearch(rows, '&').length, 1);
	assert.equal(filterBySearch(rows, 'reliable & high').length, 1);
});

test('filterBySearch returns all rows unchanged for an empty or blank query', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	assert.equal(filterBySearch(rows, '').length, rows.length);
	assert.equal(filterBySearch(rows, '   ').length, rows.length);
});

test('filterBySearch returns an empty array when nothing matches', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026);
	assert.deepEqual(filterBySearch(rows, 'no such author or affiliation'), []);
});

test('filterBySearch does not change rank — it only narrows which rows are shown', () => {
	const rows = getFilteredRows(sampleData(), 1988, 2026); // Bob and Alice tie at rank 1
	const matches = filterBySearch(rows, 'bob');
	assert.equal(matches[0].rank, 1);
});

test('buildCSV emits a header row followed by one CRLF-joined row per author', () => {
	const rows = [
		{ rank: 1, author: 'Alice A.', papers: 5, affiliation: 'Uni A' },
		{ rank: 3, author: 'Carol C.', papers: 3, affiliation: 'Uni C' },
	];
	assert.equal(
		buildCSV(rows),
		'Rank,Author,Papers,Affiliation\r\n1,Alice A.,5,Uni A\r\n3,Carol C.,3,Uni C'
	);
});

test('buildCSV returns just the header for an empty row set', () => {
	assert.equal(buildCSV([]), 'Rank,Author,Papers,Affiliation');
});

test('buildCSV quotes fields containing a comma', () => {
	const rows = [{ rank: 1, author: 'Alice A.', papers: 5, affiliation: 'MIT, USA' }];
	assert.match(buildCSV(rows), /"MIT, USA"/);
});

test('buildCSV quotes fields containing a quote character and doubles it', () => {
	const rows = [{ rank: 1, author: 'Al "Ace" A.', papers: 5, affiliation: 'Uni A' }];
	assert.match(buildCSV(rows), /"Al ""Ace"" A\."/);
});

test('buildCSV quotes fields containing an embedded newline', () => {
	const rows = [{ rank: 1, author: 'Alice A.', papers: 5, affiliation: 'Line1\nLine2' }];
	assert.match(buildCSV(rows), /"Line1\nLine2"/);
});

test('buildCSV decodes HTML entities in author and affiliation before writing them out', () => {
	const rows = [{ rank: 1, author: 'A &amp; B', papers: 1, affiliation: 'Reliable &amp; High' }];
	const csv = buildCSV(rows);
	assert.match(csv, /A & B/);
	assert.match(csv, /Reliable & High/);
	assert.doesNotMatch(csv, /&amp;/);
});

test('buildCSV leaves fields with no special characters unquoted', () => {
	const rows = [{ rank: 1, author: 'Alice A.', papers: 5, affiliation: 'Uni A' }];
	assert.doesNotMatch(buildCSV(rows), /"/);
});
