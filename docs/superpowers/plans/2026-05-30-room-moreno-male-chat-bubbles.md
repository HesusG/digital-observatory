# Moreno Male Sprite Swap + Periodic Chat Bubbles (Iteración C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer a Moreno hombre intercambiando su sprite con tess (char_0 + hue-shift), y mostrar bocadillos de diálogo periódicos (cada ~8s, ~3s) a la derecha de Moreno y Hesus con frases rotativas.

**Architecture:** Solo frontend (`room/webview-ui`). Las paletas se fijan por seed y se propagan vía `agentCreated` → `addAgent`. Las frases viven en un módulo de datos + helper puro `pickPhrase` (testeable). El timing corre en `officeState.update`; el render es un overlay DOM nuevo (`ChatBubbleOverlay`) que posiciona el globo a la derecha del personaje (patrón de `ToolOverlay`).

**Tech Stack:** React 19, TypeScript, Canvas, Tailwind v4, Vite, `node --test` + `tsx`.

**Nota de proceso:** `git commit` ha segfalleado en este repo. Ejecutar git SECUENCIAL (nunca en paralelo), con rutas absolutas o `git -C /mnt/data/repos/digital-observatory`, y si aparece `.git/index.lock` borrarlo antes de reintentar.

---

### Task 1: Datos de frases + helper puro `pickPhrase` + tests

**Files:**
- Create: `room/webview-ui/src/office/engine/chatLines.ts`
- Test: `room/webview-ui/test/chatLines.test.ts`

- [ ] **Step 1: Write the failing test**

`room/webview-ui/test/chatLines.test.ts`:
```ts
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { HESUS_LINES, MORENO_LINES, pickPhrase } from '../src/office/engine/chatLines.ts';

test('both lists have at least 8 phrases', () => {
  assert.ok(HESUS_LINES.length >= 8);
  assert.ok(MORENO_LINES.length >= 8);
});

test('pickPhrase never repeats the previous index (list >= 2)', () => {
  const lines = ['a', 'b', 'c'];
  // rand=0 would pick index 0; if prev=0 it must shift off it.
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
  // prev=-1, rand picks floor(0.5*4)=2
  const r = pickPhrase(lines, -1, () => 0.5);
  assert.equal(r.index, 2);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd room/webview-ui && npm test`
Expected: FAIL — `Cannot find module '.../chatLines.ts'`.

- [ ] **Step 3: Write minimal implementation**

`room/webview-ui/src/office/engine/chatLines.ts`:
```ts
// Ambient chat phrases for the boss characters + a pure phrase picker.
// pickPhrase is DOM-free and accepts an injectable rand for deterministic tests.

export const HESUS_LINES: string[] = [
  'Si bro!',
  'tengo miedo',
  '¿crees que me vaya a morir?',
  '¿y si truena el servidor?',
  'no me dejes solo bro',
  'esto se va a caer, lo sé',
  '¿viste eso? qué miedo',
  '¿seguro que esto es seguro?',
];

export const MORENO_LINES: string[] = [
  'uff!',
  'medio día',
  'el mercado nunca duerme',
  'yo ya lo había predicho',
  'eso es ruido, no señal',
  'mis valuaciones nunca fallan',
  'esto es alfa puro',
  'los amateurs venden, yo acumulo',
];

// Pick a random phrase, avoiding an immediate repeat of prevIndex when possible.
export function pickPhrase(
  lines: string[],
  prevIndex: number,
  rand: () => number = Math.random,
): { index: number; text: string } {
  if (lines.length <= 1) return { index: 0, text: lines[0] ?? '' };
  let index = Math.floor(rand() * lines.length);
  if (index >= lines.length) index = lines.length - 1;
  if (index === prevIndex) index = (index + 1) % lines.length;
  return { index, text: lines[index] };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd room/webview-ui && npm test`
Expected: PASS (4 nuevos + existentes).

- [ ] **Step 5: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/office/engine/chatLines.ts room/webview-ui/test/chatLines.test.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): boss chat phrases + pure pickPhrase helper + tests"
```

---

### Task 2: Campos de chat en el modelo + constantes

**Files:**
- Modify: `room/webview-ui/src/office/types.ts` (interface `Character`)
- Modify: `room/webview-ui/src/office/engine/characters.ts` (`createCharacter` return)
- Modify: `room/webview-ui/src/constants.ts`

- [ ] **Step 1: Add Character fields**

En `room/webview-ui/src/office/types.ts`, dentro de `interface Character`, junto a
`isBoss?`/`isPlayer?` (que ya existen), añadir:
```ts
  /** Ambient chat phrases for this character (only bosses) */
  chatLines?: string[];
  /** Currently-visible chat phrase, or null */
  chatText: string | null;
  /** Countdown: visible-time while chatText set, else cooldown until next phrase */
  chatTimer: number;
  /** Index of the last shown phrase (avoid immediate repeat) */
  chatPrevIndex: number;
```

- [ ] **Step 2: Initialize in createCharacter**

En `room/webview-ui/src/office/engine/characters.ts`, en el objeto que retorna
`createCharacter`, antes de `inputTokens: 0,`, añadir:
```ts
    chatText: null,
    chatTimer: 0,
    chatPrevIndex: -1,
```
(`chatLines` queda `undefined` por defecto; se asigna solo a los jefes.)

- [ ] **Step 3: Add timing constants**

En `room/webview-ui/src/constants.ts`, al final del archivo, añadir:
```ts
export const CHAT_BUBBLE_VISIBLE_SEC = 3;
export const CHAT_BUBBLE_GAP_MIN_SEC = 7;
export const CHAT_BUBBLE_GAP_MAX_SEC = 10;
```

- [ ] **Step 4: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde (los campos nuevos se usan en Tasks 3-5; `chatText/chatTimer/chatPrevIndex` ya están inicializados, así que no hay error de "missing property").

- [ ] **Step 5: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/office/types.ts room/webview-ui/src/office/engine/characters.ts room/webview-ui/src/constants.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): Character chat fields + chat timing constants"
```

---

### Task 3: Mensaje + siembra de paletas (swap) y chatLines

**Files:**
- Modify: `room/core/src/messages.ts` (`AgentCreated`)
- Modify: `room/webview-ui/src/transport/eventTranslate.ts` (`SeedAgent`, `SEED_AGENTS`)
- Modify: `room/webview-ui/src/transport/sseTransport.ts` (emit)

- [ ] **Step 1: Extend AgentCreated**

En `room/core/src/messages.ts`, en `interface AgentCreated` (que hoy termina tras
`isPlayer?: boolean;`), añadir antes del cierre `}`:
```ts
  palette?: number;
  hueShift?: number;
  chatLines?: string[];
```

- [ ] **Step 2: Extend SeedAgent + SEED_AGENTS (palette swap + chat)**

En `room/webview-ui/src/transport/eventTranslate.ts`, ampliar la interfaz:
```ts
export interface SeedAgent {
  name: string;
  id: number;
  displayName: string;
  isBoss?: boolean;
  isPlayer?: boolean;
  palette?: number;
  hueShift?: number;
  chatLines?: string[];
}
```
Importar las frases arriba del archivo (junto a otros imports):
```ts
import { HESUS_LINES, MORENO_LINES } from '../office/engine/chatLines.js';
```
Y reemplazar `SEED_AGENTS` por:
```ts
export const SEED_AGENTS: SeedAgent[] = [
  { name: 'tess', id: 1, displayName: 'tess', palette: 4 },
  { name: 'carla', id: 2, displayName: 'carla', palette: 1 },
  { name: 'edu', id: 3, displayName: 'edu', palette: 2 },
  { name: 'pablo', id: 4, displayName: 'pablo', palette: 3 },
  {
    name: 'moreno',
    id: 5,
    displayName: 'Moreno',
    isBoss: true,
    palette: 0,
    hueShift: 35,
    chatLines: MORENO_LINES,
  },
  {
    name: 'hesus',
    id: 6,
    displayName: 'Hesus',
    isBoss: true,
    isPlayer: true,
    palette: 5,
    chatLines: HESUS_LINES,
  },
];
```

- [ ] **Step 3: Pass palette/hueShift/chatLines in the emit**

En `room/webview-ui/src/transport/sseTransport.ts`, en el `this.emit({ type: 'agentCreated', ... })`
dentro del `for (const a of SEED_AGENTS)`, añadir los campos:
```ts
      this.emit({
        type: 'agentCreated',
        id: a.id,
        folderName: a.displayName,
        displayName: a.displayName,
        isBoss: a.isBoss,
        isPlayer: a.isPlayer,
        palette: a.palette,
        hueShift: a.hueShift,
        chatLines: a.chatLines,
      });
```

- [ ] **Step 4: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde.

- [ ] **Step 5: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/core/src/messages.ts room/webview-ui/src/transport/eventTranslate.ts room/webview-ui/src/transport/sseTransport.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): seed fixed palettes (Moreno/tess swap) + chat lines"
```

---

### Task 4: Aplicar paleta + chatLines en addAgent/identity + timing en update

**Files:**
- Modify: `room/webview-ui/src/hooks/useExtensionMessages.ts`
- Modify: `room/webview-ui/src/office/engine/officeState.ts`

- [ ] **Step 1: Thread palette/hueShift/chatLines through the handler**

En `room/webview-ui/src/hooks/useExtensionMessages.ts`, en la rama no-teammate de
`agentCreated`, sustituir:
```ts
        } else {
          os.addAgent(id, undefined, undefined, undefined, undefined, folderName);
          os.setAgentIdentity(id, {
            displayName: msg.displayName as string | undefined,
            isBoss: msg.isBoss as boolean | undefined,
            isPlayer: msg.isPlayer as boolean | undefined,
          });
        }
```
por:
```ts
        } else {
          os.addAgent(
            id,
            msg.palette as number | undefined,
            msg.hueShift as number | undefined,
            undefined,
            undefined,
            folderName,
          );
          os.setAgentIdentity(id, {
            displayName: msg.displayName as string | undefined,
            isBoss: msg.isBoss as boolean | undefined,
            isPlayer: msg.isPlayer as boolean | undefined,
            chatLines: msg.chatLines as string[] | undefined,
          });
        }
```

- [ ] **Step 2: setAgentIdentity accepts chatLines + seed timer**

En `room/webview-ui/src/office/engine/officeState.ts`, cambiar la firma y cuerpo de
`setAgentIdentity`:
```ts
  setAgentIdentity(
    id: number,
    opts: { displayName?: string; isBoss?: boolean; isPlayer?: boolean; chatLines?: string[] },
  ): void {
    const ch = this.characters.get(id);
    if (!ch) return;
    if (opts.displayName) ch.agentName = opts.displayName;
    if (opts.isBoss) ch.isBoss = true;
    if (opts.chatLines && opts.chatLines.length > 0) {
      ch.chatLines = opts.chatLines;
      // Stagger the first phrase so the two bosses don't speak in lockstep.
      ch.chatTimer = CHAT_BUBBLE_GAP_MIN_SEC + (id % 3);
    }
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

- [ ] **Step 3: Import chat helpers/constants in officeState**

En `room/webview-ui/src/office/engine/officeState.ts`, añadir imports:
```ts
import { pickPhrase } from './chatLines.js';
```
y añadir las tres constantes al import existente de `'../../constants.js'`
(`CHAT_BUBBLE_VISIBLE_SEC, CHAT_BUBBLE_GAP_MIN_SEC, CHAT_BUBBLE_GAP_MAX_SEC`).

- [ ] **Step 4: Tick chat timer in update loop**

En `room/webview-ui/src/office/engine/officeState.ts`, en `update(dt)`, dentro del
`for (const ch of this.characters.values())`, junto al bloque que decrementa el
bubbleTimer de 'waiting' (≈ línea 808), añadir el tick de chat:
```ts
      // Ambient chat bubbles for boss characters
      if (ch.chatLines && ch.chatLines.length > 0) {
        ch.chatTimer -= dt;
        if (ch.chatTimer <= 0) {
          if (ch.chatText) {
            // Was visible → hide and start the gap until the next phrase.
            ch.chatText = null;
            ch.chatTimer =
              CHAT_BUBBLE_GAP_MIN_SEC +
              Math.random() * (CHAT_BUBBLE_GAP_MAX_SEC - CHAT_BUBBLE_GAP_MIN_SEC);
          } else {
            // Gap elapsed → show a fresh phrase.
            const picked = pickPhrase(ch.chatLines, ch.chatPrevIndex);
            ch.chatText = picked.text;
            ch.chatPrevIndex = picked.index;
            ch.chatTimer = CHAT_BUBBLE_VISIBLE_SEC;
          }
        }
      }
```
> Nota: este tick va FUERA de cualquier `continue` previo del jugador. El jugador
> (Hesus) se enruta a `updatePlayer` con `continue` antes de llegar aquí — por eso
> el tick de chat debe ejecutarse ANTES de la rama `if (ch.isPlayer) { ... continue }`.
> Colocar este bloque inmediatamente después de la apertura del `for` y del manejo
> de `matrixEffect` (que ya hace `continue`), y ANTES de la rama del jugador.

- [ ] **Step 5: Verify build + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: verde; tests PASS.

- [ ] **Step 6: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/hooks/useExtensionMessages.ts room/webview-ui/src/office/engine/officeState.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): apply palette/chatLines on create; tick ambient chat in update"
```

---

### Task 5: Render del bocadillo de texto (`ChatBubbleOverlay`)

**Files:**
- Create: `room/webview-ui/src/office/components/ChatBubbleOverlay.tsx`
- Modify: `room/webview-ui/src/App.tsx` (import + mount)

- [ ] **Step 1: Create the overlay component**

`room/webview-ui/src/office/components/ChatBubbleOverlay.tsx`:
```tsx
import { useEffect, useState } from 'react';

import type { OfficeState } from '../engine/officeState.js';
import { CharacterState, TILE_SIZE } from '../types.js';
import { CHARACTER_SITTING_OFFSET_PX, TOOL_OVERLAY_VERTICAL_OFFSET } from '../../constants.js';

interface ChatBubbleOverlayProps {
  officeState: OfficeState;
  agents: number[];
  containerRef: React.RefObject<HTMLDivElement | null>;
  zoom: number;
  panRef: React.RefObject<{ x: number; y: number }>;
}

// DOM overlay that draws ambient chat bubbles to the RIGHT of any character
// whose chatText is set (the boss characters). Mirrors ToolOverlay's screen math.
export function ChatBubbleOverlay({
  officeState,
  agents,
  containerRef,
  zoom,
  panRef,
}: ChatBubbleOverlayProps) {
  const [, setTick] = useState(0);
  useEffect(() => {
    let rafId = 0;
    const tick = () => {
      setTick((n) => n + 1);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, []);

  const el = containerRef.current;
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const canvasW = Math.round(rect.width * dpr);
  const canvasH = Math.round(rect.height * dpr);
  const layout = officeState.getLayout();
  const mapW = layout.cols * TILE_SIZE * zoom;
  const mapH = layout.rows * TILE_SIZE * zoom;
  const deviceOffsetX = Math.floor((canvasW - mapW) / 2) + Math.round(panRef.current.x);
  const deviceOffsetY = Math.floor((canvasH - mapH) / 2) + Math.round(panRef.current.y);

  return (
    <>
      {agents.map((id) => {
        const ch = officeState.characters.get(id);
        if (!ch || !ch.chatText) return null;
        const sittingOffset = ch.state === CharacterState.TYPE ? CHARACTER_SITTING_OFFSET_PX : 0;
        // Right of the character, roughly at head height.
        const screenX = (deviceOffsetX + ch.x * zoom) / dpr + 18;
        const screenY =
          (deviceOffsetY + (ch.y + sittingOffset - TOOL_OVERLAY_VERTICAL_OFFSET) * zoom) / dpr;
        return (
          <div
            key={id}
            className="absolute pixel-panel px-6 py-3 text-sm whitespace-nowrap pointer-events-none"
            style={{ left: screenX, top: screenY, zIndex: 43 }}
          >
            {ch.chatText}
          </div>
        );
      })}
    </>
  );
}
```

- [ ] **Step 2: Mount in App.tsx**

En `room/webview-ui/src/App.tsx`:
1. Import (junto al de ToolOverlay, línea ~21):
```ts
import { ChatBubbleOverlay } from './office/components/ChatBubbleOverlay.js';
```
2. Inmediatamente DESPUÉS del bloque `<ToolOverlay ... />` (que cierra en `/>`),
añadir:
```tsx
          <ChatBubbleOverlay
            officeState={officeState}
            agents={agents}
            containerRef={containerRef}
            zoom={editor.zoom}
            panRef={editor.panRef}
          />
```

- [ ] **Step 3: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde.

- [ ] **Step 4: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/office/components/ChatBubbleOverlay.tsx room/webview-ui/src/App.tsx
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): ChatBubbleOverlay renders ambient phrases to the right of bosses"
```

---

### Task 6: Build final, dist, PR y deploy

**Files:**
- Modify: `room/dist/webview/**`

- [ ] **Step 1: Build limpio + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: build verde; tests PASS. Anotar el nuevo hash `index-*.js` de
`room/dist/webview/index.html` (`grep -oE 'index-[A-Za-z0-9_-]+\.(js|css)'`).

- [ ] **Step 2: Stage dist (SECUENCIAL; borrar index.lock si aparece)**

```bash
cd /mnt/data/repos/digital-observatory
git add room/dist/webview/index.html
git add room/dist/webview/assets/<nuevo-index>.js
git add room/dist/webview/assets/<nuevo-index>.css
git add room/dist/webview/assets/<viejo-index>.js   # captura el borrado
git add room/dist/webview/assets/<viejo-index>.css
git ls-files --stage room/dist/webview/assets | grep -oE 'index-[A-Za-z0-9_-]+\.(js|css)'
```

- [ ] **Step 3: Commit dist + push**

```bash
git -C /mnt/data/repos/digital-observatory commit -m "build(room): dist for Moreno male + chat bubbles (iteración C)"
git -C /mnt/data/repos/digital-observatory push origin room-ui-2
```

- [ ] **Step 4: PR**

```bash
gh pr create --base main --head room-ui-2 \
  --title "feat(room): Moreno hombre (swap sprite) + bocadillos de diálogo" \
  --body "Swap de paletas tess↔Moreno (Moreno = char_0 + hueShift 35, tess = char_4); bocadillos de texto a la derecha de Moreno y Hesus cada ~8s/~3s con frases rotativas (≥8 c/u, sin repetir la inmediata). Helper pickPhrase con tests. Solo frontend."
```

- [ ] **Step 5: Merge (usuario) + deploy (con consentimiento)**

```bash
ssh nano-spud 'cd /home/d3r/repos/digital-observatory && git pull --ff-only origin main && docker compose up -d --build observatory'
```

- [ ] **Step 6: Verificar (descarta caché)**

```bash
curl -sS http://100.84.156.15:8400/room/index.html | grep -oE 'index-[A-Za-z0-9_-]+\.js'   # == nuevo hash
curl -sS http://100.84.156.15:8400/room/assets/<nuevo-index>.js | grep -oE 'Si bro!|alfa puro|tengo miedo' | sort -u
curl -sS -I http://100.84.156.15:8400/room/index.html | grep -i cache-control
```
Visual (incógnito + DevTools): Moreno se ve hombre (sprite distinto al de antes),
tess cambió de sprite; cada ~8s Moreno y Hesus muestran una frase a su derecha ~3s.

---

## Notas de ejecución
- TDD aplica a Task 1. Resto: motor/UI verificado por build (TS estricto:
  `noUnusedLocals`/`noUnusedParameters`) + tests + visual.
- Git SECUENCIAL siempre; si segfalla y deja `.git/index.lock`, borrarlo y reintentar; verificar con `git status` qué quedó realmente commiteado.
- `Math.random` solo en runtime (update loop); el helper `pickPhrase` se testea con `rand` inyectado.
