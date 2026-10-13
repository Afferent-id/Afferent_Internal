// Sign-in page: no language or theme buttons, language follows the browser, server errors stay in the chosen language.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function load(file, modules = {}) {
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, {
    exports, require: name => { if (name in modules) return modules[name]; throw new Error(`unexpected import ${name}`); },
  });
  return exports;
}

const page = fs.readFileSync('src/app/auth/page.tsx', 'utf8');
assert.ok(!/LanguageSwitch|ThemeToggle/.test(page), 'sign-in renders neither the language nor the theme buttons');
assert.ok(/useTheme\(\)/.test(page), 'the theme still follows the system on the sign-in page');
assert.ok(!/login-lang/.test(fs.readFileSync('src/app/auth/auth.css', 'utf8')), 'no leftover styles for the removed buttons');
assert.match(fs.readFileSync('src/app/auth/auth.css', 'utf8'), /\.login-story h2 \{[^}]*font-weight: 700/, 'headline is bold');

const messages = load('src/i18n/messages.ts');
const { pickBrowserLanguage } = load('src/i18n/browserLanguage.ts', { '@/i18n/messages': messages });
assert.equal(pickBrowserLanguage(['id-ID', 'en']), 'id');
assert.equal(pickBrowserLanguage(['ID']), 'id');
assert.equal(pickBrowserLanguage(['fr-FR', 'id']), 'id', 'first supported language wins');
assert.equal(pickBrowserLanguage(['fr-FR', 'de']), 'en', 'English fallback');
assert.equal(pickBrowserLanguage([]), 'en');
assert.equal(pickBrowserLanguage(undefined), 'en');

// Every back-end error code the page knows has a sentence in both languages, so errors follow the automatic language.
const codes = /KNOWN_CODES = \[([^\]]+)\]/.exec(page)[1].match(/'([A-Z_]+)'/g).map(c => c.slice(1, -1));
for (const lang of ['en', 'id']) {
  for (const code of codes) {
    const key = code === 'INVALID_OTP' ? 'auth.code.INVALID_OTP.plain' : `auth.code.${code}`;
    assert.ok(messages.MESSAGES[lang][key], `${lang} message for ${code}`);
  }
  for (const key of ['auth.err.signin', 'auth.err.code', 'auth.err.invalidCode', 'auth.err.resend']) assert.ok(messages.MESSAGES[lang][key], `${lang} ${key}`);
}
console.log('PASS: sign-in has no language/theme buttons, follows browser language with English fallback, and has server errors in both languages');
