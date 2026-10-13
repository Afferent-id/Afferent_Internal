// Spot the Fake and Daily quiz: one column grid, equal portal columns, choices under their portal, spacing from --space-* tokens.
const assert = require('node:assert/strict');
const fs = require('node:fs');

const css = fs.readFileSync('src/app/employee.css', 'utf8');
const rule = selector => { const match = css.split('\n').find(line => line.startsWith(selector)); assert.ok(match, `rule ${selector}`); return match; };

assert.match(rule('.game-portals, .game-choices'), /repeat\(2, minmax\(0, 1fr\)\)/, 'portals and the choices below them share the same two columns');
assert.match(rule('.game-portals, .game-choices'), /gap: var\(--space-6\)/, 'one gutter for both');
assert.match(rule('.game-wrap'), /max-width: 960px/, 'both games use the same column width');
assert.match(rule('.game-portal '), /grid-template-rows: auto 1fr/, 'portal frames stretch to the same height');
for (const selector of ['.game-wrap', '.game-card ', '.game-answer ', '.quiz-options', '.quiz-block ']) assert.match(rule(selector), /var\(--space-\d+\)/, `${selector} uses spacing tokens`);
assert.match(css, /\.fake-browser, \.fake-browser > \* \{ min-width: 0; \}/, 'long addresses cannot push the page wider on phones');
const phone = css.split('\n').find(line => line.startsWith('@media (max-width: 640px) { .game-card'));
assert.ok(phone && /\.game-portals, \.game-choices, \.game-compare-grid \{ grid-template-columns: minmax\(0, 1fr\)/.test(phone), 'one column on phones');
console.log('PASS: game pages share one grid, gutter and spacing scale');
