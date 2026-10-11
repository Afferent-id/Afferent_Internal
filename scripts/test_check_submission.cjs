// Disposable Git fixtures; never changes the working repository or contacts a provider.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');

const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'afferent-submission-guard-'));
const guard = path.join(fixture, 'scripts/check_submission.cjs');
fs.mkdirSync(path.dirname(guard));
fs.copyFileSync(path.join(__dirname, 'check_submission.cjs'), guard);
execFileSync('git', ['init', '-q'], { cwd: fixture });
const write = (name, content) => {
  const target = path.join(fixture, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
};
const check = (...args) => {
  const result = spawnSync(process.execPath, [guard, ...args], { encoding: 'utf8' });
  if (result.error) throw result.error;
  return result;
};

write('backend/models/domain_v3/classifier.joblib', Buffer.alloc(2 * 1024 * 1024));
assert.equal(check().status, 0, 'small runtime model must remain publishable');
write('new-training-corpus.csv', Buffer.alloc(10 * 1024 * 1024 + 1));
assert.equal(check().status, 1, 'oversized corpus must fail');
fs.unlinkSync(path.join(fixture, 'new-training-corpus.csv'));
write('candidate.safetensors', 'offline checkpoint');
assert.equal(check().status, 1, 'checkpoint must fail even when small');
fs.unlinkSync(path.join(fixture, 'candidate.safetensors'));
write('backend/models/char_bilstm.pt', Buffer.alloc(4 * 1024 * 1024));
assert.equal(check().status, 0, 'existing compatibility artifact must stay publishable');
write('part-a.bin', Buffer.alloc(10 * 1024 * 1024));
write('part-b.bin', Buffer.alloc(10 * 1024 * 1024));
assert.equal(check().status, 1, 'aggregate repository budget must fail');
fs.unlinkSync(path.join(fixture, 'part-a.bin'));
fs.unlinkSync(path.join(fixture, 'part-b.bin'));
write('versioned.bin', Buffer.alloc(10 * 1024 * 1024 + 1));
execFileSync('git', ['add', '--', 'versioned.bin'], { cwd: fixture });
write('versioned.bin', 'small working copy');
assert.equal(check('--staged').status, 1, 'index size must not be hidden by a smaller working copy');
fs.unlinkSync(path.join(fixture, 'versioned.bin'));
assert.equal(check('--staged').status, 1, 'an indexed file missing from the working copy must still be checked');
write('secret.txt', ['-----BEGIN ', 'PRIVATE KEY-----'].join(''));
assert.equal(check().status, 1, 'secret checks must remain active');
console.log('Submission guard: 8 regression checks passed.');
// Delete only the exact task-owned temporary directory after validating its scope.
assert.equal(path.dirname(fixture), path.resolve(os.tmpdir()));
assert.ok(path.basename(fixture).startsWith('afferent-submission-guard-'));
fs.rmSync(fixture, { recursive: true, force: true });
