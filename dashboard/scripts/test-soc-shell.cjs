// Shared admin shell: navy/teal sidebar stays readable in both themes; inbox keeps its structure.
const assert = require('node:assert/strict');
const fs = require('node:fs');

const css = fs.readFileSync('src/app/sidebar-soc.css', 'utf8');
const lum = hex => { const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const token = (source, name) => new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(source)?.[1];

const light = css.slice(0, css.indexOf(':root[data-theme="dark"] .shell[data-role] .sb { --sidebar-bg'));
const dark = css.slice(css.indexOf(':root[data-theme="dark"] .shell[data-role] .sb { --sidebar-bg'));
const themes = { light: { bg: token(light, '--sidebar-bg'), muted: token(light, '--text-muted'), text: token(light, '--text-secondary'), strong: token(light, '--text-primary') },
  dark: { bg: token(dark, '--sidebar-bg'), muted: token(light, '--text-muted'), text: token(light, '--text-secondary'), strong: token(light, '--text-primary') } };
for (const [name, c] of Object.entries(themes)) {
  assert.ok(luminance(c.bg) < 0.03, `${name} sidebar is dark`);
  const source = name === 'light' ? light : dark;
  const stops = /--sidebar-gradient:\s*linear-gradient\(([^;]+)\)/.exec(source)?.[1].match(/#[0-9a-fA-F]{6}/g) || [c.bg];
  for (const background of stops) for (const key of ['muted', 'text', 'strong']) assert.ok(ratio(c[key], background) >= 4.5, `${name} ${key} text reaches 4.5:1 on every gradient stop`);
}
function luminance(hex) { return lum(hex); }
assert.match(fs.readFileSync('src/components/admin/DashboardLayout.tsx', 'utf8'), /data-role=\{role\}/, 'the shell tells the stylesheet which role it is');
assert.match(css, /\.shell\[data-role\] \.sb/, 'all admin roles share the original sidebar palette');

const inbox = fs.readFileSync('src/components/admin/SecurityInboxSection.tsx', 'utf8');
assert.ok(!/inbox-title/.test(inbox) && !/t\('inbox\.title'\)\}<\/h3>/.test(inbox), 'no second "Security inbox" title');
assert.ok(inbox.indexOf('className="exec-kpis"') < inbox.indexOf('className="ops-toolbar"'), 'figures come first, then tabs');
assert.ok(/className="ops-page" aria-label=\{t\('inbox\.title'\)\}/.test(inbox) && /inbox\.refresh/.test(inbox), 'region still named; refresh kept');
console.log('PASS: admin sidebar gradients have readable text; Security inbox keeps its layout');
