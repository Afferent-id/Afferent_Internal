// Loading, empty and error are three different states for every list, table and chart, in English and Indonesian.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const load = file => { const mod = {}; vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: mod }); return mod; };
const { loadState } = load('src/lib/loadState.ts');

assert.equal(loadState(true, null, false).status, 'loading', 'first load');
assert.equal(loadState(false, null, false).status, 'ready', 'answered with nothing: the empty state belongs to the component');
assert.equal(loadState(false, 'HTTP 500', false).status, 'error', 'failed with nothing to show');
assert.equal(loadState(true, 'HTTP 500', false).status, 'error', 'a retry in progress after a failure still shows the error');
assert.equal(loadState(false, 'HTTP 500', true).status, 'ready', 'a failed refresh never wipes data that is on screen');
assert.equal(loadState(true, null, true).status, 'ready', 'refreshing keeps showing the data');

const messages = load('src/i18n/messages.ts').MESSAGES;
const files = fs.readdirSync('src/components/admin').map(f => `src/components/admin/${f}`).concat(['src/components/ui/LoadGate.tsx']);
const gated = ['LeaderboardSection', 'EmployeeRosterSection', 'LoginHistorySection', 'PolicySection', 'ThreatCacheSection', 'GophishCampaignSection', 'OverviewSection', 'TremorDonutCard', 'ProxyOperationsSection', 'ExecutiveSummary'];
for (const name of gated) assert.ok(/<LoadGate/.test(fs.readFileSync(`src/components/admin/${name}.tsx`, 'utf8')), `${name} separates loading and error from empty`);
for (const key of new Set(files.flatMap(f => [...fs.readFileSync(f, 'utf8').matchAll(/errorTitle="([a-z.]+)"/g)].map(m => m[1])))) {
  for (const lang of ['en', 'id']) assert.ok(messages[lang][key], `${lang} text for ${key}`);
}
for (const lang of ['en', 'id']) for (const key of ['state.error.title', 'state.error.why', 'state.empty.title', 'state.loading', 'common.retry']) assert.ok(messages[lang][key], `${lang} ${key}`);
for (const page of ['soc', 'grc', 'ciso', 'phishing-admin']) assert.ok(/loadState\(/.test(fs.readFileSync(`src/app/dashboard/${page}/page.tsx`, 'utf8')), `${page} page passes feed states down`);
console.log('PASS: every list, table and chart tells loading, empty and error apart (EN and ID); a failed refresh keeps old data');
