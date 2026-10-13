// Blocked page and phishing lesson: two-column enterprise layout that keeps the real access request, EN/ID and dark mode.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const read = file => fs.readFileSync(file, 'utf8');
const blocked = read('src/app/blocked/page.tsx');
const edu = read('src/app/simulation/education/page.tsx');
const screen = read('src/components/ui/SecurityScreen.tsx');
const css = read('src/app/security-pages.css');

for (const [name, source] of [['blocked', blocked], ['education', edu]]) assert.ok(source.includes('<SecurityScreen'), `${name} uses the two-column layout`);
assert.ok(/LanguageSwitch/.test(screen) && /ThemeToggle/.test(screen), 'language and theme controls stay in the layout');
assert.ok(/fetch\('\/api\/access-requests', \{\s*method: 'POST'/.test(blocked), 'Request access still posts a real request to the security team');
assert.ok(/domain, reason: reason\.trim\(\)/.test(blocked), 'the request carries the domain and the reason');
assert.ok(/phase === 'failed'[\s\S]*role="alert"/.test(blocked), 'a failed request is announced and the text is kept');
assert.ok(/href="\/auth"/.test(blocked), 'signed-out people are sent to sign in, not left at a dead end');
assert.ok(/grid-template-columns: 1\.04fr 1fr/.test(css) && /max-width: 800px[\s\S]*grid-template-columns: 1fr/.test(css), 'two columns on desktop, one on narrow screens');
assert.ok(/max-width: 560px/.test(css), 'phone layout');

const messages = {};
vm.runInNewContext(ts.transpileModule(read('src/i18n/messages.ts'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports: messages });
const used = new Set([...(blocked + edu).matchAll(/\bt\('([a-z0-9.]+)'/g)].map(m => m[1]));
for (const key of used) for (const lang of ['en', 'id']) assert.ok(messages.MESSAGES[lang][key], `${lang} text for ${key}`);
console.log('PASS: blocked page and phishing lesson keep the access request, sign-in path, EN/ID and the two-column layout');
