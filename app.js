(function () {
	'use strict';

	// Design tokens sourced from dsn-hof.html's :root custom properties, so the chart palette
	// stays in sync with the page's CSS instead of duplicating the same hex values in JS.
	const rootStyle = getComputedStyle(document.documentElement);
	const cssColor = (name, fallback) => rootStyle.getPropertyValue(name).trim() || fallback;
	const INK_PRIMARY = cssColor('--ink-primary', '#0b0b0b');
	const INK_SECONDARY = cssColor('--ink-secondary', '#52514e');
	const INK_MUTED = cssColor('--ink-muted', '#898781');
	const GRIDLINE = cssColor('--gridline', '#e1e0d9');
	const SURFACE = cssColor('--surface', '#fcfcfb');
	const ACCENT = cssColor('--accent', '#2a78d6');

	// Palette (validated categorical order, see dataviz skill's palette.md). Only the first slot
	// (the page's --accent) is shared with the CSS; the rest are compare-mode-only series colors.
	const CATEGORICAL = [ACCENT, '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
	const SEQUENTIAL_LINE = CATEGORICAL[0];
	const SEQUENTIAL_FILL = 'rgba(42, 120, 214, 0.10)';

	const MAX_COMPARE_SERIES = 8;

	let allData = [];
	let dataByName = new Map();
	const selectedAuthors = new Set();
	let minYear = 1988;
	let maxYear = new Date().getFullYear();
	let fromYear = minYear;
	let toYear = maxYear;
	let sortKey = 'rank';
	let sortDir = 'asc';
	let chartMode = 'trend';
	let searchQuery = '';
	let chart = null;
	let authorChart = null;
	const {
		decodeEntities,
		computeYearBounds,
		getFilteredRows: computeFilteredRows,
		sortRows: sortRowsBy,
		filterBySearch,
		yearRangeArray: rangeArray,
		topNByPapers,
		buildCSV,
		createColorAssigner,
	} = DSNLogic;
	const colorFor = createColorAssigner(CATEGORICAL);

	function populateYearSelects() {
		const fromSel = document.getElementById('fromYear');
		const toSel = document.getElementById('toYear');
		fromSel.innerHTML = '';
		toSel.innerHTML = '';
		for (let y = minYear; y <= maxYear; y++) {
			const o1 = document.createElement('option');
			o1.value = String(y);
			o1.textContent = String(y);
			fromSel.appendChild(o1);

			const o2 = document.createElement('option');
			o2.value = String(y);
			o2.textContent = String(y);
			toSel.appendChild(o2);
		}
	}

	// The single place that writes fromYear/toYear state into the two <select> elements —
	// called from render() so every state-changing handler stays DOM-sync-free.
	function syncYearSelects() {
		document.getElementById('fromYear').value = String(fromYear);
		document.getElementById('toYear').value = String(toYear);
	}

	function getFilteredRows() {
		return computeFilteredRows(allData, fromYear, toYear);
	}

	// Range-scoped rows further narrowed by the search box. Rank stays scoped to the full
	// year-range standings (computed in getFilteredRows), so searching never renumbers ranks.
	function getVisibleRows() {
		return filterBySearch(getFilteredRows(), searchQuery);
	}

	function renderTable(rows) {
		const tbody = document.getElementById('rankingBody');
		tbody.innerHTML = '';
		for (const row of rows) {
			const tr = document.createElement('tr');

			const cSelect = document.createElement('td');
			cSelect.className = 'col-select';
			const checkbox = document.createElement('input');
			checkbox.type = 'checkbox';
			checkbox.checked = selectedAuthors.has(row.author);
			checkbox.setAttribute('aria-label', `Select ${decodeEntities(row.author)} for comparison`);
			checkbox.addEventListener('change', () => {
				if (checkbox.checked) selectedAuthors.add(row.author);
				else selectedAuthors.delete(row.author);
				render();
			});
			cSelect.appendChild(checkbox);

			const cRank = document.createElement('td');
			cRank.className = 'numer3';
			cRank.textContent = row.rank;

			const cAuthor = document.createElement('td');
			cAuthor.className = 'numer1';
			const authorBtn = document.createElement('button');
			authorBtn.type = 'button';
			authorBtn.className = 'author-link';
			authorBtn.textContent = decodeEntities(row.author);
			authorBtn.addEventListener('click', () => openAuthorModal(row));
			cAuthor.appendChild(authorBtn);

			const cPapers = document.createElement('td');
			cPapers.className = 'numer2';
			cPapers.textContent = row.papers;

			const cAffil = document.createElement('td');
			cAffil.className = 'numer1';
			cAffil.textContent = decodeEntities(row.affiliation || '');

			tr.append(cSelect, cRank, cAuthor, cPapers, cAffil);
			tbody.appendChild(tr);
		}

		document.querySelectorAll('th.sortable .arrow').forEach((el) => (el.textContent = ''));
		const activeHeader = document.querySelector(`th.sortable[data-sort="${sortKey}"] .arrow`);
		if (activeHeader) activeHeader.textContent = sortDir === 'asc' ? '▲' : '▼';
	}

	function renderSummary(rows) {
		const el = document.getElementById('resultSummary');
		const query = searchQuery.trim();
		const matchClause = query ? ` matching "${query}"` : '';
		el.textContent = `Showing ${rows.length} of ${allData.length} authors${matchClause} with papers between ${fromYear}–${toYear}.`;
	}

	function updatePresetButtons() {
		const buttons = document.querySelectorAll('#presetRow button');
		buttons.forEach((btn) => {
			const preset = btn.dataset.preset;
			let match = false;
			if (preset === 'all') match = fromYear === minYear && toYear === maxYear;
			else {
				const span = parseInt(preset, 10);
				match = toYear === maxYear && fromYear === Math.max(minYear, maxYear - span + 1);
			}
			btn.classList.toggle('active', match);
		});
	}

	function updateChartModeButtons() {
		document.querySelectorAll('#chartModeRow button').forEach((btn) => {
			btn.classList.toggle('active', btn.dataset.mode === chartMode);
		});
	}

	function renderChart(rows) {
		const years = rangeArray(fromYear, toYear);
		const ctx = document.getElementById('rankingChart').getContext('2d');

		let datasets;
		let showLegend;

		if (chartMode === 'trend') {
			const totals = years.map((y) =>
				rows.reduce((sum, e) => sum + ((e.years || {})[String(y)] || 0), 0)
			);
			datasets = [{
				label: 'Papers per year',
				data: totals,
				borderColor: SEQUENTIAL_LINE,
				backgroundColor: SEQUENTIAL_FILL,
				fill: true,
				borderWidth: 2,
				borderCapStyle: 'round',
				borderJoinStyle: 'round',
				tension: 0.15,
				pointRadius: 3,
				pointHoverRadius: 5,
				pointBackgroundColor: SEQUENTIAL_LINE,
				pointBorderColor: SURFACE,
				pointBorderWidth: 2,
			}];
			showLegend = false;
			document.getElementById('chartNote').textContent =
				rows.length === 0 && searchQuery.trim() ? 'No authors match your search.' : '';
		} else {
			const selectedEntries = [...selectedAuthors]
				.map((name) => dataByName.get(name))
				.filter(Boolean)
				.sort((a, b) => b.total - a.total);
			const overflow = selectedEntries.length > MAX_COMPARE_SERIES;
			const plotted = selectedEntries.slice(0, MAX_COMPARE_SERIES);

			const noteEl = document.getElementById('chartNote');
			if (selectedEntries.length === 0) {
				noteEl.textContent = 'Select authors from the table below, or use Top 5 / Top 10.';
			} else if (overflow) {
				noteEl.textContent = `Showing ${MAX_COMPARE_SERIES} of ${selectedEntries.length} selected authors — deselect some for clarity.`;
			} else {
				noteEl.textContent = '';
			}

			datasets = plotted.map((author) => {
				const color = colorFor(author.author);
				return {
					label: decodeEntities(author.author),
					data: years.map((y) => (author.years || {})[String(y)] || 0),
					borderColor: color,
					backgroundColor: color,
					fill: false,
					borderWidth: 2,
					borderCapStyle: 'round',
					borderJoinStyle: 'round',
					tension: 0.15,
					pointRadius: 3,
					pointHoverRadius: 5,
					pointBackgroundColor: color,
					pointBorderColor: SURFACE,
					pointBorderWidth: 2,
				};
			});
			showLegend = true;
		}

		if (chart) {
			chart.destroy();
		}

		chart = new Chart(ctx, {
			type: 'line',
			data: { labels: years, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						display: showLegend,
						position: 'bottom',
						labels: { color: INK_SECONDARY, usePointStyle: true, pointStyle: 'line' },
					},
					tooltip: {
						backgroundColor: INK_PRIMARY,
						titleColor: '#fff',
						bodyColor: '#fff',
						padding: 10,
						boxPadding: 4,
					},
				},
				scales: {
					x: {
						grid: { display: false },
						ticks: { color: INK_MUTED },
						border: { color: '#c3c2b7' },
					},
					y: {
						beginAtZero: true,
						grid: { color: GRIDLINE },
						ticks: { color: INK_MUTED, precision: 0 },
						border: { display: false },
						title: { display: true, text: chartMode === 'trend' ? 'Papers (all authors)' : 'Papers', color: INK_SECONDARY },
					},
				},
			},
		});
	}

	function openAuthorModal(row) {
		const dialog = document.getElementById('authorModal');
		document.getElementById('modalName').textContent = decodeEntities(row.author);
		document.getElementById('modalAffiliation').textContent = decodeEntities(row.affiliation || 'Affiliation unknown');

		const statsEl = document.getElementById('modalStats');
		statsEl.innerHTML = '';
		const stats = [
			{ label: `All-time (${minYear}–${maxYear})`, value: `${row.allTimeTotal} papers · rank #${row.allTimeRank}` },
			{ label: `Selected range (${fromYear}–${toYear})`, value: `${row.papers} papers · rank #${row.rank}` },
		];
		for (const s of stats) {
			const wrap = document.createElement('div');
			const strong = document.createElement('strong');
			strong.textContent = s.value;
			const label = document.createElement('span');
			label.textContent = s.label;
			wrap.append(strong, label);
			statsEl.appendChild(wrap);
		}

		const years = rangeArray(minYear, maxYear);
		const counts = years.map((y) => (row.years || {})[String(y)] || 0);

		if (authorChart) authorChart.destroy();
		const ctx = document.getElementById('authorChart').getContext('2d');
		authorChart = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: years,
				datasets: [{
					label: 'Papers',
					data: counts,
					backgroundColor: SEQUENTIAL_LINE,
					borderRadius: 4,
					maxBarThickness: 22,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: INK_PRIMARY,
						titleColor: '#fff',
						bodyColor: '#fff',
						padding: 10,
						boxPadding: 4,
					},
				},
				scales: {
					x: {
						grid: { display: false },
						ticks: { color: INK_MUTED, autoSkip: true, maxRotation: 0 },
						border: { color: '#c3c2b7' },
					},
					y: {
						beginAtZero: true,
						grid: { color: GRIDLINE },
						ticks: { color: INK_MUTED, precision: 0 },
						border: { display: false },
					},
				},
			},
		});

		dialog.showModal();
	}

	function wireModal() {
		const dialog = document.getElementById('authorModal');
		document.getElementById('modalClose').addEventListener('click', () => dialog.close());
		dialog.addEventListener('click', (e) => {
			if (e.target === dialog) dialog.close();
		});
	}

	function selectTopN(n) {
		const rows = getVisibleRows();
		selectedAuthors.clear();
		topNByPapers(rows, n).forEach((name) => selectedAuthors.add(name));
		chartMode = 'compare';
		render(rows);
	}

	function clearSelection() {
		selectedAuthors.clear();
		render();
	}

	// Exports exactly what's currently on screen: the visible (range + search filtered) rows,
	// in the current sort order.
	function exportCSV() {
		const rows = sortRowsBy(getVisibleRows(), sortKey, sortDir);
		const csv = buildCSV(rows);
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `dsn-hall-of-fame_${fromYear}-${toYear}.csv`;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
	}

	function updateCompareUI() {
		const isCompare = chartMode === 'compare';
		document.getElementById('compareControls').style.display = isCompare ? '' : 'none';
		document.getElementById('rank').classList.toggle('compare-mode', isCompare);

		const summaryEl = document.getElementById('selectionSummary');
		if (isCompare) {
			summaryEl.style.display = '';
			const n = selectedAuthors.size;
			summaryEl.textContent = `${n} author${n === 1 ? '' : 's'} selected for comparison.`;
		} else {
			summaryEl.style.display = 'none';
		}
	}

	function render(precomputedRows) {
		let rows = precomputedRows || getVisibleRows();
		rows = sortRowsBy(rows, sortKey, sortDir);
		syncYearSelects();
		renderTable(rows);
		renderSummary(rows);
		updatePresetButtons();
		updateChartModeButtons();
		updateCompareUI();
		renderChart(rows);
	}

	function clampRange() {
		fromYear = Math.min(Math.max(fromYear, minYear), maxYear);
		toYear = Math.min(Math.max(toYear, minYear), maxYear);
		if (fromYear > toYear) toYear = fromYear;
	}

	function wireControls() {
		const searchInput = document.getElementById('searchInput');
		const clearSearchBtn = document.getElementById('clearSearchBtn');
		let searchDebounce = null;
		searchInput.addEventListener('input', (e) => {
			searchQuery = e.target.value;
			clearSearchBtn.style.display = searchQuery ? '' : 'none';
			clearTimeout(searchDebounce);
			searchDebounce = setTimeout(render, 150);
		});
		clearSearchBtn.addEventListener('click', () => {
			searchQuery = '';
			searchInput.value = '';
			clearSearchBtn.style.display = 'none';
			searchInput.focus();
			render();
		});

		document.getElementById('exportCsvBtn').addEventListener('click', exportCSV);

		document.getElementById('fromYear').addEventListener('change', (e) => {
			fromYear = parseInt(e.target.value, 10);
			clampRange();
			render();
		});
		document.getElementById('toYear').addEventListener('change', (e) => {
			toYear = parseInt(e.target.value, 10);
			clampRange();
			render();
		});

		document.getElementById('presetRow').addEventListener('click', (e) => {
			const btn = e.target.closest('button[data-preset]');
			if (!btn) return;
			const preset = btn.dataset.preset;
			if (preset === 'all') {
				fromYear = minYear;
				toYear = maxYear;
			} else {
				const span = parseInt(preset, 10);
				toYear = maxYear;
				fromYear = Math.max(minYear, maxYear - span + 1);
			}
			render();
		});

		document.getElementById('chartModeRow').addEventListener('click', (e) => {
			const btn = e.target.closest('button[data-mode]');
			if (!btn) return;
			chartMode = btn.dataset.mode;
			if (chartMode === 'compare' && selectedAuthors.size === 0) {
				selectTopN(5);
				return;
			}
			render();
		});

		document.getElementById('topNRow').addEventListener('click', (e) => {
			const btn = e.target.closest('button[data-topn]');
			if (btn) {
				selectTopN(parseInt(btn.dataset.topn, 10));
				return;
			}
			if (e.target.id === 'clearSelectionBtn') {
				clearSelection();
			}
		});

		document.querySelectorAll('th.sortable').forEach((th) => {
			th.addEventListener('click', () => {
				const key = th.dataset.sort;
				if (sortKey === key) {
					sortDir = sortDir === 'asc' ? 'desc' : 'asc';
				} else {
					sortKey = key;
					sortDir = key === 'papers' ? 'desc' : 'asc';
				}
				render();
			});
		});
	}

	async function init() {
		const resp = await fetch('./ranking.json');
		allData = await resp.json();
		dataByName = new Map(allData.map((e) => [e.author, e]));

		const bounds = computeYearBounds(allData, { min: minYear, max: maxYear });
		minYear = bounds.min;
		maxYear = bounds.max;
		fromYear = minYear;
		toYear = maxYear;

		populateYearSelects();
		wireControls();
		wireModal();
		render();
	}

	document.addEventListener('DOMContentLoaded', init);
})();
