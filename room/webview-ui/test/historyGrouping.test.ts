import assert from 'node:assert/strict';
import { test } from 'node:test';

import { bandOf, localDayKey, localTimeLabel } from '../src/components/historyGrouping.ts';

test('bandOf: mañana is [6,12)', () => {
  assert.equal(bandOf(new Date(2026, 4, 29, 6, 0)), 'manana');
  assert.equal(bandOf(new Date(2026, 4, 29, 11, 59)), 'manana');
});

test('bandOf: tarde is [12,19)', () => {
  assert.equal(bandOf(new Date(2026, 4, 29, 12, 0)), 'tarde');
  assert.equal(bandOf(new Date(2026, 4, 29, 18, 59)), 'tarde');
});

test('bandOf: noche is [19,24) and [0,6)', () => {
  assert.equal(bandOf(new Date(2026, 4, 29, 19, 0)), 'noche');
  assert.equal(bandOf(new Date(2026, 4, 29, 23, 59)), 'noche');
  assert.equal(bandOf(new Date(2026, 4, 29, 0, 0)), 'noche');
  assert.equal(bandOf(new Date(2026, 4, 29, 5, 59)), 'noche');
});

test('localDayKey: zero-padded local YYYY-MM-DD', () => {
  assert.equal(localDayKey(new Date(2026, 0, 3, 10, 0)), '2026-01-03');
});

test('localTimeLabel: zero-padded HH:MM', () => {
  assert.equal(localTimeLabel(new Date(2026, 4, 29, 9, 5)), '09:05');
});
