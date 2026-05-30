import assert from 'node:assert/strict';
import { test } from 'node:test';

import { HESUS_LINES, MORENO_LINES, pickPhrase } from '../src/office/engine/chatLines.ts';

test('both lists have at least 8 phrases', () => {
  assert.ok(HESUS_LINES.length >= 8);
  assert.ok(MORENO_LINES.length >= 8);
});

test('pickPhrase never repeats the previous index (list >= 2)', () => {
  const lines = ['a', 'b', 'c'];
  const r = pickPhrase(lines, 0, () => 0);
  assert.notEqual(r.index, 0);
  assert.equal(lines[r.index], r.text);
});

test('pickPhrase with single-item list returns index 0', () => {
  const r = pickPhrase(['only'], -1, () => 0.9);
  assert.deepEqual(r, { index: 0, text: 'only' });
});

test('pickPhrase respects injected rand', () => {
  const lines = ['a', 'b', 'c', 'd'];
  const r = pickPhrase(lines, -1, () => 0.5);
  assert.equal(r.index, 2);
});
