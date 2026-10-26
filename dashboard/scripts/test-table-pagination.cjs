// User behavior: every record remains reachable, sorting spans all pages, and shrinking results recover safely.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const states = [];
let cursor = 0;
const hooks = {
  useState(initial) { const index = cursor++; if (!(index in states)) states[index] = initial; return [states[index], next => { states[index] = typeof next === 'function' ? next(states[index]) : next; }]; },
  useMemo: run => run(),
};
const words = { 'table.navigation': '{name} pagination', 'table.range': '{from}–{to} of {total}', 'table.previous': 'Previous', 'table.next': 'Next', 'table.page': 'Page {page} of {pages}' };
const source = ts.transpileModule(fs.readFileSync('src/components/ui/DataTable.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const output = {};
vm.runInNewContext(source, { exports: output, require: name => name === 'react' ? hooks : name === '@/hooks/useScrollCue' ? { useScrollCue: () => [{ current: null }, ''] } : name === '@/i18n/I18nProvider' ? { useI18n: () => ({ t: (key, vars = {}) => words[key].replace(/\{(\w+)\}/g, (_, field) => String(vars[field])) }) } : require(name) });
const all = Array.from({ length: 7 }, (_, index) => ({ id: `row-${index + 1}`, score: 7 - index }));
let rows = all;
const text = tree => tree == null || typeof tree === 'boolean' ? '' : Array.isArray(tree) ? tree.map(text).join('') : typeof tree === 'object' ? text(tree.props?.children) : String(tree);
const nodes = tree => Array.isArray(tree) ? tree.flatMap(nodes) : !tree || typeof tree !== 'object' ? [] : [tree, ...nodes(tree.props?.children)];
function render() { cursor = 0; return output.default({ caption: 'Records', rows, columns: [{ key: 'id', header: 'ID', render: r => r.id }, { key: 'score', header: 'Score', sortValue: r => r.score, render: r => r.score }], pageSize: 3, rowKey: r => r.id }); }
const ids = tree => nodes(nodes(tree).find(n => n.type === 'tbody')).filter(n => n.type === 'tr').map(n => text(nodes(n).find(cell => cell.type === 'td')));
const button = (tree, label) => nodes(tree).find(n => n.type === 'button' && text(n) === label);
let tree = render();
assert.deepEqual(ids(tree), ['row-1', 'row-2', 'row-3']);
assert.equal(button(tree, 'Previous').props.disabled, true);
button(tree, 'Next').props.onClick(); tree = render();
assert.deepEqual(ids(tree), ['row-4', 'row-5', 'row-6']);
button(tree, 'Next').props.onClick(); tree = render();
assert.deepEqual(ids(tree), ['row-7']);
assert.equal(button(tree, 'Next').props.disabled, true);
button(tree, 'Score').props.onClick(); tree = render();
assert.deepEqual(ids(tree), ['row-7', 'row-6', 'row-5'], 'sort applies to the complete data set and returns to page one');
button(tree, 'Next').props.onClick(); render();
rows = all.slice(0, 1); tree = render();
assert.deepEqual(ids(tree), ['row-1']);
assert.equal(button(tree, 'Next').props.disabled, true);
rows = all; tree = render();
assert.deepEqual(ids(tree), ['row-7', 'row-6', 'row-5'], 'new data does not revive a page removed by a previous refresh');
console.log('PASS: pagination reaches every record, sorts before paging, and stays on a valid page after refresh');
