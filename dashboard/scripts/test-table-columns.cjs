// Tables never cut a column without a sign: low-priority columns drop out in narrow boxes, and what still overflows shows a scroll shadow and can be scrolled by keyboard.
const assert = require('node:assert/strict');
const fs = require('node:fs');

const table = fs.readFileSync('src/components/ui/DataTable.tsx', 'utf8');
const css = fs.readFileSync('src/app/ui.css', 'utf8');
const queue = fs.readFileSync('src/components/admin/IncidentQueue.tsx', 'utf8');

assert.ok(/role="region" aria-label=\{caption\} tabIndex=\{0\}/.test(table), 'the scroll box is a labelled, focusable region (keyboard scrolling)');
assert.ok(/data-low=/.test(table) && /low\?: boolean/.test(table), 'tables can mark low-priority columns');
assert.match(css, /@container \(max-width: 640px\) \{ \.data-table :is\(th, td\)\[data-secondary\]/, 'other tables keep their 640px rule');
assert.match(css, /@container \(max-width: 760px\) \{ \.incident-split \.data-table :is\(th, td\)\[data-secondary\]/, 'only the incident list drops secondary columns below 760px');
assert.match(css, /@container \(max-width: 560px\) \{ \.data-table :is\(th, td\)\[data-low\] \{ display: none; \}/, 'low-priority columns drop out below 560px');
assert.match(css, /\.table-wrap\[data-more~="right"\] \{ box-shadow: inset/, 'a shadow marks a cut edge');
const hook = fs.readFileSync('src/hooks/useScrollCue.ts', 'utf8');
assert.ok(/data-more=\{more \|\| undefined\}/.test(table) && /useScrollCue\(/.test(table) && /scrollLeft \+ node\.clientWidth < node\.scrollWidth/.test(hook), 'the cue only appears when the table really overflows');
assert.ok(!/\.table-wrap \{\s*background:/.test(css), 'a table that fits is drawn exactly as before');
assert.match(css, /\.table-wrap:focus-visible/, 'the scroll box shows keyboard focus');
const incidentColumns = queue.slice(queue.indexOf('const columns'), queue.indexOf('const detail'));
for (const key of ['severity', 'incident', 'status']) assert.ok(!new RegExp(`key: '${key}'[^\\n]*(low|secondary): true`).test(incidentColumns), `${key} always stays`);
assert.ok(/key: 'age'[^\n]*low: true/.test(incidentColumns) && /key: 'id'[^\n]*low: true/.test(incidentColumns), 'ID and age are the first to go on phones');
console.log('PASS: incident table keeps its key columns, never silently cuts the last one, and scrolls with a visible cue');
