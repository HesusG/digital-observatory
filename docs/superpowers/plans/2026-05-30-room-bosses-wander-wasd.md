# Room Bosses + Glow Names + Idle Wander + WASD (Iteración B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir dos personajes fijos (Moreno NPC, Hesus jugador) con nombre dorado + glow + 👑, hacer que workers idle y Moreno deambulen, mostrar el nombre de todos los personajes, y mover a Hesus con WASD.

**Architecture:** Solo frontend (`room/webview-ui`). Los jefes se siembran en `sseTransport.ts` junto a los workers. El movimiento WASD reusa el sistema WALK+lerp por tiles; un helper puro `stepTile` (testeable con node:test) calcula el tile vecino y se valida con `isWalkable`. Los nombres se renderizan siempre en `ToolOverlay` (línea de nombre fuera del gate de hover/select), con estilo jefe cuando `isBoss`.

**Tech Stack:** React 19, TypeScript, Canvas, Tailwind v4, Vite, `node --test` + `tsx`.

---

### Task 1: Helper puro `stepTile` + tests

**Files:**
- Create: `room/webview-ui/src/office/engine/playerMove.ts`
- Test: `room/webview-ui/test/playerMove.test.ts`

- [ ] **Step 1: Write the failing test**

`room/webview-ui/test/playerMove.test.ts`:
```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd room/webview-ui && npm test`
Expected: FAIL — `Cannot find module '.../playerMove.ts'`.

- [ ] **Step 3: Write minimal implementation**

`room/webview-ui/src/office/engine/playerMove.ts`:
```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd room/webview-ui && npm test`
Expected: PASS (4 nuevos + los existentes).

- [ ] **Step 5: Commit**

```bash
git add room/webview-ui/src/office/engine/playerMove.ts room/webview-ui/test/playerMove.test.ts
git commit -m "feat(room): pure stepTile/inputDirection helpers for WASD + tests"
```

---

### Task 2: Campos `isBoss`/`isPlayer` + input de jugador en el modelo

**Files:**
- Modify: `room/webview-ui/src/office/types.ts` (interface `Character`)
- Modify: `room/webview-ui/src/office/engine/officeState.ts` (campo `playerInput`)

- [ ] **Step 1: Add fields to Character**

En `room/webview-ui/src/office/types.ts`, dentro de `interface Character` (después de `isSubagent`/`parentAgentId`, antes de `matrixEffect`), añadir:
```ts
  /** Boss styling: gold glow + crown on the name label */
  isBoss?: boolean;
  /** WASD-controlled player character (skips wander AI) */
  isPlayer?: boolean;
```

- [ ] **Step 2: Add player input + seed flag to OfficeState**

En `room/webview-ui/src/office/engine/officeState.ts`, junto a los campos públicos (después de `cameraFollowId`), añadir:
```ts
  /** WASD input state for the player character (set by usePlayerControls) */
  playerInput = { up: false, down: false, left: false, right: false };
```

Importar el tipo arriba (junto a otros imports de engine):
```ts
import { stepTile, inputDirection } from './playerMove.js';
```

- [ ] **Step 3: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde (imports usados en Task 4; si `stepTile`/`inputDirection` quedaran sin usar este paso podría avisar — en ese caso completar Task 4 antes de buildear; ver nota). 

> Nota de ejecución: para evitar el error temporal de import sin usar, hacer Steps 1-2 y el import de Task 4 (Step 1) juntos antes del primer `npm run build`. Commit tras Task 2 sin build intermedio.

- [ ] **Step 4: Commit**

```bash
git add room/webview-ui/src/office/types.ts room/webview-ui/src/office/engine/officeState.ts
git commit -m "feat(room): Character isBoss/isPlayer + OfficeState.playerInput"
```

---

### Task 3: Censo de siembra de jefes (`eventTranslate.ts`)

**Files:**
- Modify: `room/webview-ui/src/transport/eventTranslate.ts`

- [ ] **Step 1: Add boss IDs + seed table**

En `room/webview-ui/src/transport/eventTranslate.ts`, ampliar `AGENT_IDS` y añadir la tabla de siembra justo debajo de `AGENT_ORDER`:
```ts
export const AGENT_IDS: Record<string, number> = {
  tess: 1,
  carla: 2,
  edu: 3,
  pablo: 4,
  moreno: 5,
  hesus: 6,
};

export const AGENT_ORDER = ['tess', 'carla', 'edu', 'pablo'] as const;

// Full cast seeded on connect (workers + bosses). Bosses get gold glow + crown;
// Hesus is WASD-controlled. displayName is shown above every character.
export interface SeedAgent {
  name: string;
  id: number;
  displayName: string;
  isBoss?: boolean;
  isPlayer?: boolean;
}

export const SEED_AGENTS: SeedAgent[] = [
  { name: 'tess', id: 1, displayName: 'tess' },
  { name: 'carla', id: 2, displayName: 'carla' },
  { name: 'edu', id: 3, displayName: 'edu' },
  { name: 'pablo', id: 4, displayName: 'pablo' },
  { name: 'moreno', id: 5, displayName: 'Moreno', isBoss: true },
  { name: 'hesus', id: 6, displayName: 'Hesus', isBoss: true, isPlayer: true },
];
```

- [ ] **Step 2: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde.

- [ ] **Step 3: Commit**

```bash
git add room/webview-ui/src/transport/eventTranslate.ts
git commit -m "feat(room): seed table with Moreno + Hesus bosses"
```

---

### Task 4: Aplicar identidad (nombre/jefe/jugador) + WASD en el motor

**Files:**
- Modify: `room/webview-ui/src/office/engine/officeState.ts` (`setAgentIdentity`, update loop)
- Modify: `room/webview-ui/src/office/engine/characters.ts` (rama `isPlayer`)
- Modify: `room/webview-ui/src/hooks/useExtensionMessages.ts` (handler `agentCreated`)
- Modify: `room/webview-ui/src/transport/sseTransport.ts` (siembra + idle inicial)
- Reference: `core/src/messages.ts` (campos opcionales del mensaje)

- [ ] **Step 1: Extend agentCreated message type**

En `room/core/src/messages.ts`, en el miembro de la unión `agentCreated` (líneas ~60-71, donde está `folderName?: string;` junto a `isTeammate?`/`teammateName?`), añadir campos opcionales:
```ts
  displayName?: string;
  isBoss?: boolean;
  isPlayer?: boolean;
```

- [ ] **Step 2: Add setAgentIdentity to OfficeState**

En `officeState.ts`, añadir un método (cerca de `setAgentActive`):
```ts
  setAgentIdentity(
    id: number,
    opts: { displayName?: string; isBoss?: boolean; isPlayer?: boolean },
  ): void {
    const ch = this.characters.get(id);
    if (!ch) return;
    if (opts.displayName) ch.agentName = opts.displayName;
    if (opts.isBoss) ch.isBoss = true;
    if (opts.isPlayer) {
      ch.isPlayer = true;
      // Player roams freely and the camera follows it.
      if (ch.seatId) {
        const seat = this.seats.get(ch.seatId);
        if (seat) seat.assigned = false;
        ch.seatId = null;
      }
      ch.isActive = false;
      this.cameraFollowId = id;
    }
  }
```

- [ ] **Step 3: Drive WASD in the update loop**

En `officeState.ts`, dentro de `update(dt)`, justo antes de la llamada a `withOwnSeatUnblocked(...)` (oficeState.ts ~línea 743), interceptar al jugador:
```ts
      if (ch.isPlayer) {
        this.updatePlayer(ch, dt);
        continue;
      }
```
Y añadir el método `updatePlayer` (cerca de `setAgentIdentity`):
```ts
  private updatePlayer(ch: Character, dt: number): void {
    // If mid-step, let the existing WALK lerp run via updateCharacter.
    if (ch.state === CharacterState.WALK && ch.path.length > 0) {
      updateCharacter(ch, dt, this.walkableTiles, this.seats, this.tileMap, this.blockedTiles);
      return;
    }
    const dir = inputDirection(this.playerInput);
    if (dir === null) {
      ch.state = CharacterState.IDLE;
      ch.frame = 0;
      return;
    }
    ch.dir = dir;
    const next = stepTile(ch.tileCol, ch.tileRow, dir);
    if (isWalkable(next.col, next.row, this.tileMap, this.blockedTiles)) {
      ch.path = [next];
      ch.moveProgress = 0;
      ch.state = CharacterState.WALK;
    } else {
      ch.state = CharacterState.IDLE;
      ch.frame = 0;
    }
  }
```
`isWalkable`, `CharacterState`, `updateCharacter`, `stepTile`, `inputDirection` ya están importados (Tasks 2 / existentes).

- [ ] **Step 4: Apply identity in the agentCreated handler**

En `useExtensionMessages.ts`, en la rama `else` de `agentCreated` (la de no-teammate, oficeState ~línea 190-192), tras `os.addAgent(...)` añadir:
```ts
          os.addAgent(id, undefined, undefined, undefined, undefined, folderName);
          os.setAgentIdentity(id, {
            displayName: msg.displayName as string | undefined,
            isBoss: msg.isBoss as boolean | undefined,
            isPlayer: msg.isPlayer as boolean | undefined,
          });
```

- [ ] **Step 5: Seed bosses + start idle in sseTransport**

En `sseTransport.ts`, reemplazar el bloque "2. Fixed cast" (líneas 67-70) por:
```ts
    // 2. Fixed cast (workers + bosses), then mark everyone but the player idle
    //    so workers and Moreno wander on their own; events reactivate workers.
    for (const a of SEED_AGENTS) {
      this.emit({
        type: 'agentCreated',
        id: a.id,
        folderName: a.displayName,
        displayName: a.displayName,
        isBoss: a.isBoss,
        isPlayer: a.isPlayer,
      });
    }
    for (const a of SEED_AGENTS) {
      if (!a.isPlayer) this.emit({ type: 'agentStatus', id: a.id, status: 'idle' });
    }
```
Y cambiar el import de la línea 16 para traer `SEED_AGENTS`:
```ts
import { AGENT_IDS, SEED_AGENTS, type ApiEvent, translateEvent } from './eventTranslate.js';
```
(Se elimina `AGENT_ORDER` del import si deja de usarse en este archivo; `AGENT_IDS` sigue usándose por `translateEvent`. Verificar y quitar imports sin usar para `noUnusedLocals`.)

- [ ] **Step 6: Verify build + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: build verde; tests PASS.

- [ ] **Step 7: Commit**

```bash
git add room/core/src/messages.ts room/webview-ui/src/office/engine/officeState.ts room/webview-ui/src/office/engine/characters.ts room/webview-ui/src/hooks/useExtensionMessages.ts room/webview-ui/src/transport/sseTransport.ts
git commit -m "feat(room): seed bosses, apply identity, WASD player movement, start idle"
```

---

### Task 5: Hook de teclado WASD (`usePlayerControls.ts`)

**Files:**
- Create: `room/webview-ui/src/hooks/usePlayerControls.ts`
- Modify: `room/webview-ui/src/App.tsx` (montar el hook)

- [ ] **Step 1: Create the hook**

`room/webview-ui/src/hooks/usePlayerControls.ts`:
```ts
import { useEffect } from 'react';

import type { OfficeState } from '../office/engine/officeState.js';

// Listens for WASD (and arrow keys) and writes into officeState.playerInput.
// Disabled while editing the layout or while typing in an input/textarea.
export function usePlayerControls(
  getOfficeState: () => OfficeState,
  isEditMode: boolean,
): void {
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
```

- [ ] **Step 2: Mount in App.tsx**

En `room/webview-ui/src/App.tsx`:
1. Añadir el import (junto a los otros hooks):
```ts
import { usePlayerControls } from './hooks/usePlayerControls.js';
```
2. Dentro del componente `App`, tras `const editor = useEditorActions(...)`, llamar:
```ts
  usePlayerControls(getOfficeState, editor.isEditMode);
```

- [ ] **Step 3: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde.

- [ ] **Step 4: Commit**

```bash
git add room/webview-ui/src/hooks/usePlayerControls.ts room/webview-ui/src/App.tsx
git commit -m "feat(room): WASD keyboard hook wired into App"
```

---

### Task 6: Nombres siempre visibles + estilo jefe (glow + 👑)

**Files:**
- Modify: `room/webview-ui/src/constants.ts` (colores jefe)
- Modify: `room/webview-ui/src/office/components/ToolOverlay.tsx`

- [ ] **Step 1: Add boss colors**

En `room/webview-ui/src/constants.ts`, junto a `TEAM_LEAD_COLOR`/`TEAM_ROLE_COLOR`:
```ts
export const BOSS_NAME_COLOR = '#ffd700';
export const BOSS_NAME_GLOW = '0 0 6px rgba(255,215,0,0.9), 0 0 14px rgba(255,170,0,0.5)';
```

- [ ] **Step 2: Always render the name; style bosses**

En `ToolOverlay.tsx`:
1. Importar los colores nuevos (en el bloque de import de `../../constants.js`): añadir `BOSS_NAME_COLOR, BOSS_NAME_GLOW`.
2. Sustituir, dentro del `.map`, el cálculo de `teamRoleLabel` (línea ~157) por un nombre mostrable universal:
```ts
        const displayName = ch.agentName ?? ch.folderName ?? (ch.isTeamLead ? 'LEAD' : null);
```
3. Renderizar SIEMPRE una línea de nombre encima del personaje, **fuera** del gate de hover/select. Como el contenedor `div` (línea ~162) hoy solo se devuelve cuando pasa el gate de la línea 120, mover la etiqueta de nombre a su propio bloque que se devuelve siempre. Reemplazar el `return (<div …>)` actual por una estructura que renderice (a) el nombre siempre y (b) el panel rico solo cuando `isSelected || isHovered || alwaysShowOverlay`.

   Concretamente, sustituir el early-return de la línea 120
   ```ts
   if (!alwaysShowOverlay && !isSelected && !isHovered) return null;
   ```
   por un flag:
   ```ts
   const showRichPanel = alwaysShowOverlay || isSelected || isHovered;
   ```
   y envolver el panel rico (el `<div className="flex items-center border-border …pixel-panel…">` … `</div>` y el medidor de tokens) en `{showRichPanel && ( … )}`.

4. Añadir, como primer hijo del contenedor posicionado (antes del panel rico), la línea de nombre:
```tsx
            {displayName && (
              <span
                className="leading-none whitespace-nowrap mb-1"
                style={{
                  fontSize: ch.isBoss ? '20px' : '16px',
                  fontWeight: ch.isBoss ? 'bold' : undefined,
                  color: ch.isBoss ? BOSS_NAME_COLOR : 'var(--color-text)',
                  textShadow: ch.isBoss ? BOSS_NAME_GLOW : undefined,
                }}
              >
                {ch.isBoss ? `👑 ${displayName}` : displayName}
              </span>
            )}
```

5. Como el nombre ahora se muestra siempre, **quitar** el bloque viejo `{teamRoleLabel && (…)}` dentro del panel rico (líneas ~182-193) para no duplicar el nombre, y dejar ahí solo `activityText` y el `folderName` (si se desea). Mantener `isTeamAgent` para el medidor de tokens.

> Resultado: cada personaje muestra su nombre siempre (workers en blanco pequeño; Moreno/Hesus en dorado con glow y corona). El panel de actividad/cerrar sigue apareciendo solo en hover/selección o con alwaysShowOverlay.

- [ ] **Step 3: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde (sin unused: si `teamRoleLabel`/`TEAM_LEAD_COLOR`/`TEAM_ROLE_COLOR` quedan sin uso, eliminarlos del código/imports).

- [ ] **Step 4: Commit**

```bash
git add room/webview-ui/src/constants.ts room/webview-ui/src/office/components/ToolOverlay.tsx
git commit -m "feat(room): always-on name labels + gold glow + crown for bosses"
```

---

### Task 7: Build final, dist, PR y deploy

**Files:**
- Modify: `room/dist/webview/**`

- [ ] **Step 1: Build limpio + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: build verde; tests PASS. Anotar el nuevo hash `index-*.js` de `room/dist/webview/index.html`.

- [ ] **Step 2: Stage dist en trozos**

```bash
cd /mnt/data/repos/digital-observatory
git add room/dist/webview/index.html
git add room/dist/webview/assets/<nuevo-index>.js
git add room/dist/webview/assets/<nuevo-index>.css
git add -A room/dist/webview/assets
git ls-tree -r HEAD --name-only room/dist/webview/assets | grep index-
```

- [ ] **Step 3: Commit dist + push**

```bash
git commit -m "build(room): dist for bosses + wander + WASD (iteración B)"
git push origin room-ui-2
```

- [ ] **Step 4: PR**

```bash
gh pr create --base main --head room-ui-2 \
  --title "feat(room): Moreno + Hesus jefes, nombres con glow, wander idle, WASD" \
  --body "Siembra de Moreno (NPC) y Hesus (jugador WASD) como jefes con nombre dorado + glow + 👑; nombres visibles para todos; workers idle y Moreno deambulan; Hesus se mueve con WASD y la cámara lo sigue. Helper stepTile/inputDirection con tests (node:test). Solo frontend."
```

- [ ] **Step 5: Merge (usuario) + deploy (con consentimiento explícito)**

En nano-spud (requiere autorización del usuario):
```bash
ssh nano-spud 'cd /home/d3r/repos/digital-observatory && git pull --ff-only origin main && docker compose up -d --build observatory'
```

- [ ] **Step 6: Verificar (descarta caché)**

```bash
curl -sS http://100.84.156.15:8400/room/index.html | grep -o 'index-[A-Za-z0-9_]*\.js'   # == nuevo hash
curl -sS -I http://100.84.156.15:8400/room/index.html | grep -i cache-control             # no-cache
```
Visual (incógnito + DevTools): aparecen 6 personajes; Moreno y Hesus con nombre dorado + glow + 👑; los workers muestran su nombre; workers y Moreno deambulan en reposo; Hesus se mueve con WASD y la cámara lo sigue; WASD no rompe el modo edición.

---

## Notas de ejecución
- TDD aplica a Task 1 (helper puro). El resto es motor/UI: verificación por `npm run build` (TS estricto: `noUnusedLocals`/`noUnusedParameters`) + tests + revisión visual.
- Si aparece import/variable sin usar (p.ej. `AGENT_ORDER`, `teamRoleLabel`, `TEAM_*_COLOR`), eliminarlo en el mismo task.
- IDs de jefes (5,6) no chocan con sub-agentes (negativos) ni con workers (1-4).
- `core/src/messages.ts`: confirmar ruta real con `git status` antes de commitear.
