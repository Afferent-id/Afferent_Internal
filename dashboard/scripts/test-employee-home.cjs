// Employee home: visible connection status, answered requests as a toast and bell item, main action above the fold.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const read = file => fs.readFileSync(file, 'utf8');
const mod = {};
vm.runInNewContext(ts.transpileModule(read('src/lib/requestNotices.ts'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: mod });
const { requestsToAnnounce, rememberAnnounced, protectionBlockVisible } = mod;

// Keep both verified outcomes visible; errors take priority over a previous successful probe.
const base = { booting: false, failedToLoad: false, registered: true, probe: 'disconnected' };
assert.equal(protectionBlockVisible(base), true, 'registered but not reaching the device: show');
assert.equal(protectionBlockVisible({ ...base, registered: false, probe: 'checking' }), true, 'not registered: show');
assert.equal(protectionBlockVisible({ ...base, probe: 'connected' }), true, 'connected status stays visible');
assert.equal(protectionBlockVisible({ ...base, probe: 'checking' }), false, 'still checking: no flash of a warning');
assert.equal(protectionBlockVisible({ ...base, booting: true }), false, 'still loading: nothing');
assert.equal(protectionBlockVisible({ ...base, booting: true, failedToLoad: true }), true, 'could not load: show with the error');
assert.equal(protectionBlockVisible({ ...base, probe: 'connected', failedToLoad: true }), true, 'a successful probe must not hide a heartbeat error');
assert.equal(protectionBlockVisible({ ...base, probe: 'checking', failedToLoad: true }), true, 'a pending probe must not hide an API error');

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
// Render the real card with fixed hook state; no requests or device/policy changes.
const { renderToStaticMarkup } = require('react-dom/server');
function renderProxy({ registered = true, probe = 'connected', error = '', booting = false } = {}) {
  const states = [{ registered, connected: true }, 'http://lab.test:3128', '', probe, '', booting, false, error, false, false];
  let cursor = 0;
  const exports = {};
  const stubs = {
    react: { ...require('react'), useCallback: fn => fn, useEffect() {}, useRef: value => ({ current: value }), useState: initial => [cursor < states.length ? states[cursor++] : initial, () => {}] },
    '@/i18n/I18nProvider': { useI18n: () => ({ lang: 'en', t: key => key }) },
    '@/components/ui/Dialog': { default: () => null },
    '@/lib/serverError': {}, '@/lib/requestNotices': mod,
    '@/lib/relativeTime': { formatAgo: () => 'now' }, '@/hooks/useNow': { useNow: () => 0 },
  };
  vm.runInNewContext(ts.transpileModule(card, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText, {
    exports, require: name => stubs[name] ?? require(name),
  });
  return renderToStaticMarkup(exports.default());
}
const connected = renderProxy();
assert.match(connected, /data-tone="ok"/, 'verified connection uses the connected style');
assert.match(connected, /proxy\.on\.title/, 'connected text stays on screen');
assert.match(connected, /role="status"/, 'status changes are announced');
assert.match(connected, /\/api\/proxy\/ca\.crt/, 'CA download remains reachable when connected');
const disconnected = renderProxy({ probe: 'disconnected' });
assert.match(disconnected, /data-tone="bad"/, 'a failed real probe overrides a stale backend connected flag');
assert.match(disconnected, /proxy\.failed\.title/, 'failed connection stays visible');
const failed = renderProxy({ error: 'Heartbeat unavailable' });
assert.match(failed, /data-tone="bad"/, 'heartbeat failure cannot appear connected');
assert.match(failed, /Heartbeat unavailable/, 'heartbeat error remains visible');
assert.doesNotMatch(renderProxy({ registered: false }), /data-tone="ok"/, 'an unregistered device is never shown as connected');
assert.doesNotMatch(renderProxy({ booting: true }), /proxy\.on\.title/, 'no connected claim during initial loading');
console.log('PASS: proxy ON/OFF and error states stay visible, answered requests use toast and bell, main action sits beside My safety');
