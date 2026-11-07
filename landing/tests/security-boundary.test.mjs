import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { canonicalHttpsUrl } from '../src/worker.js';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('HTTP and www requests canonicalize to HTTPS in one permanent redirect', () => {
  assert.equal(
    canonicalHttpsUrl('http://vibememory.io/guide?source=test'),
    'https://vibememory.io/guide?source=test'
  );
  assert.equal(
    canonicalHttpsUrl('http://www.vibememory.io/guide?source=test'),
    'https://vibememory.io/guide?source=test'
  );
  assert.equal(
    canonicalHttpsUrl('https://www.vibememory.io/'),
    'https://vibememory.io/'
  );
  assert.equal(canonicalHttpsUrl('https://vibememory.io/'), null);
});

test('browser document policy blocks clipboard reads without breaking same-origin copy', () => {
  const headers = read('public/_headers');
  assert.match(
    headers,
    /Permissions-Policy: camera=\(\), microphone=\(\), geolocation=\(\), clipboard-read=\(\), clipboard-write=\(self\)/
  );

  for (const asset of ['public/assets/app.js', 'public/assets/console.js']) {
    const source = read(asset);
    assert.doesNotMatch(source, /navigator\.clipboard\.(?:read|readText)\s*\(/);
    assert.match(source, /navigator\.clipboard\.writeText\s*\(/);
  }
});
