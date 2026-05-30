import assert from 'node:assert/strict';
import { test } from 'node:test';

import { stepTile } from '../src/office/engine/playerMove.ts';
import { Direction } from '../src/office/types.ts';

test('stepTile UP decrements row', () => {
  assert.deepEqual(stepTile(3, 5, Direction.UP), { col: 3, row: 4 });
});
test('stepTile DOWN increments row', () => {
  assert.deepEqual(stepTile(3, 5, Direction.DOWN), { col: 3, row: 6 });
});
test('stepTile LEFT decrements col', () => {
  assert.deepEqual(stepTile(3, 5, Direction.LEFT), { col: 2, row: 5 });
});
test('stepTile RIGHT increments col', () => {
  assert.deepEqual(stepTile(3, 5, Direction.RIGHT), { col: 4, row: 5 });
});
