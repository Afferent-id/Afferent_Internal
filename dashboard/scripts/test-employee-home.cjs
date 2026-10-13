// Employee home: one conditional protection block, answered requests as a toast and bell item, main action above the fold.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const read = file => fs.readFileSync(file, 'utf8');
const mod = {};
vm.runInNewContext(ts.transpileModule(read('src/lib/requestNotices.ts'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: mod });
const { requestsToAnnounce, rememberAnnounced, protectionBlockVisible } = mod;

// Protection block: hidden while checking and once it works; shown only when it is known to be off.
const base = { booting: false, failedToLoad: false, registered: true, probe: 'disconnected' };
assert.equal(protectionBlockVisible(base), true, 'registered but not reaching the device: show');
assert.equal(protectionBlockVisible({ ...base, registered: false, probe: 'checking' }), true, 'not registered: show');
assert.equal(protectionBlockVisible({ ...base, probe: 'connected' }), false, 'protection works: no block, no empty space');
assert.equal(protectionBlockVisible({ ...base, probe: 'checking' }), false, 'still checking: no flash of a warning');
assert.equal(protectionBlockVisible({ ...base, booting: true }), false, 'still loading: nothing');
assert.equal(protectionBlockVisible({ ...base, booting: true, failedToLoad: true }), true, 'could not load: show with the error');

// Access request answers: announced once, open requests never.
const requests = [
  { id: 'a', domain: 'a.example', status: 'allowed' }, { id: 'b', domain: 'b.example', status: 'open' },
  { id: 'c', domain: 'c.example', status: 'denied' }, { id: 'd', domain: 'd.example', status: 'denied' }, { id: 'e', domain: 'e.example', status: 'allowed' },
];
assert.deepEqual(requestsToAnnounce(requests, '').map(r => r.id), ['a', 'c', 'd'], 'answered only, at most three');
assert.deepEqual(requestsToAnnounce(requests, 'a,c').map(r => r.id), ['d', 'e'], 'already announced are skipped');
const stored = rememberAnnounced('a', ['c', 'a']);
assert.equal(stored, 'a,c', 'no duplicates');
assert.equal(rememberAnnounced(Array.from({ length: 60 }, (_, i) => `i${i}`).join(','), ['z']).split(',').length, 50, 'storage stays small');

const home = read('src/components/employee/EmployeeHome.tsx');
assert.ok(!/emp-notice|notice\.dismiss/.test(home), 'no persistent notice at the top of the page');
assert.ok(/toast\.show\(/.test(home) && /durationMs: [6-9]\d{3}|durationMs: \d{5}/.test(home), 'the toast stays long enough to read');
assert.ok(/ProxyConnectionCard \/>/.test(home) && !/emp-protect|emp-next/.test(home), 'a single protection block');
assert.ok(home.indexOf('emp-area-safety') < home.indexOf('emp-area-scanner'), 'My safety first, then the main action');
assert.match(read('src/components/ui/Toast.tsx'), /role="status" aria-live="polite"/, 'toasts are read out by screen readers');
const bell = read('src/components/NotificationBell.tsx');
assert.ok(/notif\.req\.allowed/.test(bell) && /notif\.req\.denied/.test(bell), 'answers are also in the notification bell');
assert.ok(/afferent_toasted_requests/.test(home) && !/afferent_toasted_requests/.test(bell), 'the toast does not mark the bell item as read');
const css = read('src/app/employee.css');
assert.match(css, /grid-template-areas: "scanner" "safety" "activity"/, 'main action first on narrow screens');
const card = read('src/components/ProxyConnectionCard.tsx');
assert.ok(/<details className="pxc-details">/.test(card) && /proxy\.ca/.test(card) && /proxy\.lastChecked/.test(card), 'technical details are folded inside the block');
console.log('PASS: protection block is conditional, answered requests use toast and bell, main action sits beside My safety above the fold');
