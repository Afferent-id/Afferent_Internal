// Tabs component: WAI-ARIA tablist wiring and keyboard movement.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync('src/components/ui/Tabs.tsx', 'utf8');
const mod = {};
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText, {
  exports: mod, require: name => (name === 'react' ? { useRef: () => ({ current: new Map() }) } : { jsx() {}, jsxs() {}, Fragment: 'f' }),
});
const ids = ['live', 'policies', 'threats', 'audit'];
const { nextTab, tabId, panelId } = mod;

assert.equal(nextTab(ids, 'live', 'ArrowRight'), 'policies');
assert.equal(nextTab(ids, 'audit', 'ArrowRight'), 'live', 'wraps forward');
assert.equal(nextTab(ids, 'live', 'ArrowLeft'), 'audit', 'wraps backward');
assert.equal(nextTab(ids, 'threats', 'Home'), 'live');
assert.equal(nextTab(ids, 'live', 'End'), 'audit');
assert.equal(nextTab(ids, 'live', 'ArrowDown'), null, 'other keys are left alone');
assert.equal(nextTab(ids, 'live', 'Tab'), null, 'Tab is never captured, so focus can leave the row');
assert.equal(tabId('traffic', 'live'), 'traffic-tab-live');
assert.equal(panelId('traffic', 'live'), 'traffic-panel-live');

assert.match(source, /role="tablist" aria-label=\{label\}/, 'named tablist');
assert.match(source, /role="tab"/);
assert.match(source, /aria-selected=\{selected === tab\.id\} aria-controls=\{panelId\(idPrefix, tab\.id\)\} tabIndex=\{selected === tab\.id \? 0 : -1\}/, 'selected state, controls and roving tabindex');
assert.match(source, /visually-hidden/, 'badge has a text alternative');
console.log('PASS: tabs follow the WAI-ARIA pattern (roles, roving tabindex, arrows, Home/End, wrap, Tab not captured)');
