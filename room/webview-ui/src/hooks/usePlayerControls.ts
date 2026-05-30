import { useEffect } from 'react';

import type { OfficeState } from '../office/engine/officeState.js';

// Listens for WASD (and arrow keys) and writes into officeState.playerInput.
// Disabled while editing the layout or while typing in an input/textarea.
export function usePlayerControls(getOfficeState: () => OfficeState, isEditMode: boolean): void {
  useEffect(() => {
    if (isEditMode) return;

    const keyToField = (key: string): keyof OfficeState['playerInput'] | null => {
      switch (key.toLowerCase()) {
        case 'w':
        case 'arrowup':
          return 'up';
        case 's':
        case 'arrowdown':
          return 'down';
        case 'a':
        case 'arrowleft':
          return 'left';
        case 'd':
        case 'arrowright':
          return 'right';
        default:
          return null;
      }
    };

    const isTyping = (t: EventTarget | null): boolean => {
      const el = t as HTMLElement | null;
      if (!el) return false;
      const tag = el.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable;
    };

    const set = (e: KeyboardEvent, value: boolean) => {
      if (isTyping(e.target)) return;
      const field = keyToField(e.key);
      if (!field) return;
      e.preventDefault();
      getOfficeState().playerInput[field] = value;
    };

    const onDown = (e: KeyboardEvent) => set(e, true);
    const onUp = (e: KeyboardEvent) => set(e, false);
    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup', onUp);
    return () => {
      window.removeEventListener('keydown', onDown);
      window.removeEventListener('keyup', onUp);
      // Clear any held keys when disabling.
      const pi = getOfficeState().playerInput;
      pi.up = pi.down = pi.left = pi.right = false;
    };
  }, [getOfficeState, isEditMode]);
}
