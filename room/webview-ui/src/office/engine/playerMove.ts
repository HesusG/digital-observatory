// Pure, DOM-free helper for WASD player movement: given a tile and a direction,
// returns the neighbouring tile. Caller validates walkability with isWalkable.
import { Direction } from '../types.js';
import type { Direction as Dir } from '../types.js';

export interface PlayerInput {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
}

export function stepTile(col: number, row: number, dir: Dir): { col: number; row: number } {
  switch (dir) {
    case Direction.UP:
      return { col, row: row - 1 };
    case Direction.DOWN:
      return { col, row: row + 1 };
    case Direction.LEFT:
      return { col: col - 1, row };
    case Direction.RIGHT:
      return { col: col + 1, row };
    default:
      return { col, row };
  }
}

// First active direction in WASD priority order, or null when no key is held.
export function inputDirection(input: PlayerInput): Dir | null {
  if (input.up) return Direction.UP;
  if (input.down) return Direction.DOWN;
  if (input.left) return Direction.LEFT;
  if (input.right) return Direction.RIGHT;
  return null;
}
