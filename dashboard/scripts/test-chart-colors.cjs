// Chart colours: each series is at least 3:1 against its card in both themes, and none relies on colour alone.
const assert = require('node:assert/strict');
const fs = require('node:fs');

const css = fs.readFileSync('src/app/globals.css', 'utf8');
const luminance = hex => {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const block = start => css.slice(css.indexOf(start), css.indexOf('\n}', css.indexOf(start)));
const themes = { light: { css: block(':root {'), surface: '#ffffff' }, dark: { css: block('[data-theme="dark"] {'), surface: '#152236' } };
const series = ['critical', 'high', 'medium', 'ok', 'low'];
for (const [name, theme] of Object.entries(themes)) {
  for (const key of series) {
    const hex = new RegExp(`--chart-${key}:\\s*(#[0-9a-fA-F]{6})`).exec(theme.css)?.[1];
    assert.ok(hex, `${name} token --chart-${key}`);
    assert.ok(ratio(hex, theme.surface) >= 3, `${name} ${key} ${hex} is ${ratio(hex, theme.surface).toFixed(2)}:1, needs 3:1`);
  }
}
const donut = fs.readFileSync('src/components/admin/TremorDonutCard.tsx', 'utf8');
const overview = fs.readFileSync('src/components/admin/OverviewSection.tsx', 'utf8');
assert.ok(/shape/.test(donut) && /<b>\{item\.value/.test(donut), 'donut legend has a shape and the number for every series');
assert.equal(new Set(overview.match(/shape: '(circle|triangle|diamond|square)'/g)).size, 4, 'four different shapes');
assert.ok(/LabelList/.test(overview) && /score} · \{word\}/.test(overview), 'bars carry the value and a word');
assert.ok(!/var\(--sev-(critical|high|medium|ok)\)'/.test(overview), 'charts use chart tokens, not text-status tokens');
console.log('PASS: chart colours reach 3:1 in both themes and carry shapes or labels');
