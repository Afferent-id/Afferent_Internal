// Traffic and policies: four sub-tabs on one page, same data and actions, deep link through ?view=.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const read = file => fs.readFileSync(file, 'utf8');
const mod = {};
vm.runInNewContext(ts.transpileModule(read('src/lib/trafficView.ts'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: mod, URLSearchParams });
const { viewFromSearch, searchForView, threatsNeedingAttention } = mod;

assert.equal(viewFromSearch(''), 'live', 'default tab is Live traffic');
assert.equal(viewFromSearch('?view=policies'), 'policies');
assert.equal(viewFromSearch('?view=threats'), 'threats');
assert.equal(viewFromSearch('?view=audit&x=1'), 'audit');
assert.equal(viewFromSearch('?view=signins'), 'audit', 'readable alias for the sign-in tab');
assert.equal(searchForView('audit'), '?view=audit', 'the canonical value is still written, so old links and new links agree');
assert.equal(viewFromSearch('?view=evil'), 'live', 'unknown values fall back to the default');
assert.equal(searchForView('live'), '', 'the default keeps a clean URL');
assert.equal(searchForView('audit'), '?view=audit');
assert.equal(threatsNeedingAttention([{ action: 'block' }, { action: 'NOTIFY_SOC' }, { action: 'notify_soc' }]), 2);

const wrapper = read('src/components/admin/TrafficPolicies.tsx');
const ops = read('src/components/admin/ProxyOperationsSection.tsx');
const soc = read('src/app/dashboard/soc/page.tsx');
for (const label of ['traffic.tab.live', 'traffic.tab.policies', 'traffic.tab.threats', 'traffic.tab.audit']) assert.ok(wrapper.includes(label), `${label} tab`);
assert.ok(/badge: openAlerts/.test(wrapper) && /badge: threats/.test(wrapper), 'live and threat tabs carry badges so urgent work is visible');
assert.ok(/pushState/.test(wrapper) && /popstate/.test(wrapper), 'tabs are in the URL and Back works');
// The same actions stay reachable and keep their behaviour: one component still owns state, dialog and requests.
for (const needle of ["fetch('/api/proxy/manual-decision'", '/api/proxy/alerts/${alert.id}/decision', '<Dialog open={review !== null}', 'submitReview', 'ops.dialog.confirmBlock']) assert.ok(ops.includes(needle), `kept: ${needle}`);
assert.ok(/id="traffic-panel-live"[^>]*hidden=\{view !== 'live'\}/.test(ops) && /id="traffic-panel-policies"[^>]*hidden=\{view !== 'policies'\}/.test(ops), 'panels use the tab ids and stay mounted while hidden (SSE and state keep running)');
assert.ok(/role="tabpanel" id="traffic-panel-live" aria-labelledby="traffic-tab-live"/.test(ops), 'panel is labelled by its tab');
assert.ok(/<TrafficPolicies/.test(soc) && !/<ProxyOperationsSection/.test(soc), 'SOC page uses the new page; role and route unchanged');
assert.ok(!/api\/(?!proxy|admin\/login-history)/.test(wrapper.replace(/@\/[a-zA-Z/]+/g, '')), 'no new endpoints in the wrapper');
const messages = {};
vm.runInNewContext(ts.transpileModule(read('src/i18n/messages.ts'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: messages });
const keys = [...new Set([...(wrapper + ops).matchAll(/\bt\('((?:traffic|ops)\.[a-zA-Z.]+)'/g)].map(m => m[1]))];
for (const lang of ['en', 'id']) for (const key of keys) assert.ok(messages.MESSAGES[lang][key], `${lang} ${key}`);
const css = read('src/app/ui.css');
assert.match(css, /\.tabs \{[^}]*overflow-x: auto/, 'tab row scrolls sideways on phones instead of overflowing the page');
assert.ok(/useScrollCue/.test(ops) && /role="region" aria-label=\{t\('ops\.alerts\.caption'\)\} tabIndex=\{0\}/.test(ops), 'alerts and traffic tables scroll with a cue and keyboard access on phones');
assert.match(css, /\.ops-page \.table-wrap \.data-table :is\(th, td\):last-child \{ position: sticky; right: 0/, 'the Action column stays in view on phones');
for (const [lang, text] of [['en', 'Sign-in activity'], ['id', 'Aktivitas login']]) assert.equal(messages.MESSAGES[lang]['traffic.tab.audit'], text, `${lang} label matches the authentication data actually collected`);
console.log('PASS: Traffic and policies has four URL-addressable tabs with badges, keeps every action and adds no endpoint');
