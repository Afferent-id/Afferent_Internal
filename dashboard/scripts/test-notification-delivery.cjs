// Shared delivery labels and live send eligibility; no browser or email request.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');

function load(file, dependencies = {}) {
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, { exports, require: name => dependencies[name] || require(name) });
  return exports;
}
const { en } = load('src/i18n/messages.ts');
const i18n = { useI18n: () => ({ t: (key, vars = {}) => en[key].replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? `{${name}}`) }) };
const Delivery = load('src/components/admin/NotificationDelivery.tsx', { '@/i18n/I18nProvider': i18n });
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return tree && typeof tree === 'object' ? [tree, ...nodes(tree.props?.children)] : [];
}
function text(tree) {
  if (Array.isArray(tree)) return tree.map(text).join('');
  if (tree && typeof tree === 'object') return text(tree.type === Delivery.default ? Delivery.default(tree.props) : tree.props?.children);
  return tree === false || tree == null ? '' : String(tree);
}
const delivered = { sent_at: '2026-10-27 00:00:00', last_error: null, kind: 'training', actor_role: 'phishing_admin' };
const label = value => text(Delivery.default({ delivery: value }));
assert.match(label(delivered), /Sent to Mailpit/);
assert.match(label(delivered), /Training recommendation/);
assert.match(label(delivered), /Administrator/);
assert.match(label({ ...delivered, sent_at: null }), /Queued, waiting/);
assert.match(label({ ...delivered, sent_at: null, last_error: 'SMTPUnavailable' }), /Will retry/);
assert.match(label({ ...delivered, last_error: 'skipped_not_eligible' }), /Cancelled/);
assert.doesNotMatch(label({ ...delivered, last_error: 'skipped_not_eligible' }), /Sent to Mailpit/);
assert.match(label(null), /No education email/);

const assessment = { id: 'exam-fixture', email: 'employee@demo.test', division: 'IT', status: 'completed',
  trigger_score: 50, percent: 40, correct: 6, pass_percent: 80, needs_training: 1, observations: 0,
  observationLog: [], outboxId: null, sentAt: null, deliveryError: null,
  delivery: { ...delivered, kind: 'baseline', actor_role: 'soc' }, canSend: false };
const Training = load('src/components/admin/TrainingInbox.tsx', {
  react: { useState: initial => [initial, () => {}] },
  '@/hooks/usePolling': { usePolling: () => ({ data: { assessments: [assessment] }, refresh() {} }) },
  '@/components/ui/Dialog': { default: () => null },
  '@/i18n/I18nProvider': i18n,
  './NotificationDelivery': Delivery,
});
const render = () => Training.default();
const button = tree => nodes(tree).find(node => node.type === 'button' && text(node) === 'Send training recommendation');
assert.equal(button(render()).props.disabled, true, 'a SOC email disables administrator sending');
assert.match(text(render()), /shared email cooldown/);
assert.match(text(render()), /Baseline warning/);
assessment.canSend = true;
assert.equal(button(render()).props.disabled, false, 'backend eligibility after cooldown restores the action');
assert.doesNotMatch(text(render()), /shared email cooldown/);
assessment.outboxId = 12;
assessment.sentAt = delivered.sent_at;
assert.equal(button(render()), undefined, 'an existing exam recommendation cannot be sent again');
assert.match(text(render()), /Sent to Mailpit/);
console.log('PASS: shared queued/sent/retry/cancelled labels and administrator/SOC cooldown eligibility');
