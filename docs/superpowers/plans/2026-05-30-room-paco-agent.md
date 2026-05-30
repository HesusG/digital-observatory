# Paco Agent (Boss + Sofa + Conspiracy Chat) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un 7º agente "Paco" (jefe con corona/glow, sprite char_3 + hue-shift) que arranca sentado (en sofá si hay), a ratos deambula, y suelta frases conspiranoico-depre cada ~8s.

**Architecture:** Solo frontend (`room/webview-ui`), reusando toda la maquinaria de iteraciones B/C (seed → agentCreated → addAgent/setAgentIdentity, isBoss, wander idle, chatLines + ChatBubbleOverlay). Lo único nuevo: una lista de frases, una entrada de seed con `preferSofa`, y un buscador de asiento de sofá en officeState.

**Tech Stack:** React 19, TypeScript, Canvas, Tailwind v4, Vite, `node --test` + `tsx`.

**Nota de proceso:** `git commit` ha segfalleado en este repo. Git SECUENCIAL (nunca en paralelo), con `git -C /mnt/data/repos/digital-observatory`. Si aparece `.git/index.lock`, borrarlo y reintentar; verificar con `git status` qué quedó commiteado.

---

### Task 1: Frases de Paco + test

**Files:**
- Modify: `room/webview-ui/src/office/engine/chatLines.ts`
- Modify: `room/webview-ui/test/chatLines.test.ts`

- [ ] **Step 1: Add the failing assertion**

En `room/webview-ui/test/chatLines.test.ts`, añadir el import de `PACO_LINES` y un test. Reemplazar la línea de import existente:
```ts
import { HESUS_LINES, MORENO_LINES, pickPhrase } from '../src/office/engine/chatLines.ts';
```
por:
```ts
import { HESUS_LINES, MORENO_LINES, PACO_LINES, pickPhrase } from '../src/office/engine/chatLines.ts';
```
Y añadir un test nuevo al final del archivo:
```ts
test('PACO_LINES has at least 8 phrases', () => {
  assert.ok(PACO_LINES.length >= 8);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd room/webview-ui && npm test`
Expected: FAIL — `PACO_LINES` no exportado (o `undefined`).

- [ ] **Step 3: Add PACO_LINES**

En `room/webview-ui/src/office/engine/chatLines.ts`, después de `MORENO_LINES`, añadir:
```ts
export const PACO_LINES: string[] = [
  'ya fue',
  'el unabomber tenía razón',
  'todo está conectado, ¿no lo ves?',
  'mi peor decisión financiera fue existir',
  'nos están observando',
  'ya nada tiene sentido',
  'debí vender en el pico',
  'el sistema está diseñado para que pierdas',
];
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd room/webview-ui && npm test`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/office/engine/chatLines.ts room/webview-ui/test/chatLines.test.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): Paco chat phrases + test"
```

---

### Task 2: Mensaje + buscador de asiento de sofá

**Files:**
- Modify: `room/core/src/messages.ts` (`AgentCreated`)
- Modify: `room/webview-ui/src/office/engine/officeState.ts` (`findFreeSofaSeat`)

- [ ] **Step 1: Add preferSofa to AgentCreated**

En `room/core/src/messages.ts`, en `interface AgentCreated` (que ya tiene
`palette?/hueShift?/chatLines?`), añadir antes del cierre `}`:
```ts
  preferSofa?: boolean;
```

- [ ] **Step 2: Add findFreeSofaSeat to OfficeState**

En `room/webview-ui/src/office/engine/officeState.ts`, añadir un método (cerca de
`setAgentIdentity`). Los asientos provienen de muebles `category === 'chairs'`; el
`Seat.uid` es el `uid` del mueble o `uid:N`. Mapeamos seat → mueble quitando el
sufijo `:N` y filtramos por tipo de la familia sofá/banca:
```ts
  // First free seat that belongs to a sofa/bench-type furniture, or null.
  findFreeSofaSeat(): string | null {
    const SOFA_TYPES = new Set([
      'SOFA',
      'CUSHIONED_BENCH',
      'WOODEN_BENCH',
      'CUSHIONED_CHAIR',
    ]);
    for (const [seatId, seat] of this.seats) {
      if (seat.assigned) continue;
      const furnitureUid = seatId.split(':')[0];
      const item = this.layout.furniture.find((f) => f.uid === furnitureUid);
      if (item && SOFA_TYPES.has(item.type)) return seatId;
    }
    return null;
  }
```

- [ ] **Step 3: Verify build**

Run: `cd room/webview-ui && npm run build`
Expected: verde (el método se usa en Task 3; si quedara sin uso, completar Task 3 antes del build — ver nota). 

> Nota: para evitar "método sin usar" no aplica (los métodos de clase no disparan
> noUnusedLocals). Build debe pasar igual.

- [ ] **Step 4: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/core/src/messages.ts room/webview-ui/src/office/engine/officeState.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): AgentCreated.preferSofa + OfficeState.findFreeSofaSeat"
```

---

### Task 3: Seed de Paco + propagar preferSofa

**Files:**
- Modify: `room/webview-ui/src/transport/eventTranslate.ts` (AGENT_IDS, SeedAgent, SEED_AGENTS, import)
- Modify: `room/webview-ui/src/transport/sseTransport.ts` (emit)
- Modify: `room/webview-ui/src/hooks/useExtensionMessages.ts` (preferredSeatId)

- [ ] **Step 1: Add paco to AGENT_IDS + import PACO_LINES**

En `room/webview-ui/src/transport/eventTranslate.ts`:
- Cambiar el import de frases:
```ts
import { HESUS_LINES, MORENO_LINES, PACO_LINES } from '../office/engine/chatLines.js';
```
- Añadir el id en `AGENT_IDS` (después de `hesus: 6,`):
```ts
  paco: 7,
```

- [ ] **Step 2: Extend SeedAgent + add Paco**

En el mismo archivo, añadir a `interface SeedAgent`:
```ts
  preferSofa?: boolean;
```
Y añadir al final del array `SEED_AGENTS` (después de la entrada de hesus):
```ts
  {
    name: 'paco',
    id: 7,
    displayName: 'Paco',
    isBoss: true,
    palette: 3,
    hueShift: 200,
    chatLines: PACO_LINES,
    preferSofa: true,
  },
```

- [ ] **Step 3: Pass preferSofa in the emit**

En `room/webview-ui/src/transport/sseTransport.ts`, en el `this.emit({ type: 'agentCreated', ... })`
del `for (const a of SEED_AGENTS)`, añadir el campo:
```ts
        preferSofa: a.preferSofa,
```
(Junto a `palette: a.palette, hueShift: a.hueShift, chatLines: a.chatLines`.)

- [ ] **Step 4: Resolve preferred sofa seat in the handler**

En `room/webview-ui/src/hooks/useExtensionMessages.ts`, en la rama no-teammate de
`agentCreated`, sustituir la llamada actual a `addAgent` (que pasa `undefined` como
4º arg, el `preferredSeatId`) por una que use el sofá cuando `preferSofa`:
```ts
        } else {
          const preferredSeatId =
            (msg.preferSofa as boolean | undefined) ? (os.findFreeSofaSeat() ?? undefined) : undefined;
          os.addAgent(
            id,
            msg.palette as number | undefined,
            msg.hueShift as number | undefined,
            preferredSeatId,
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

- [ ] **Step 5: Verify build + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: verde; tests PASS.

- [ ] **Step 6: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add room/webview-ui/src/transport/eventTranslate.ts room/webview-ui/src/transport/sseTransport.ts room/webview-ui/src/hooks/useExtensionMessages.ts
git -C /mnt/data/repos/digital-observatory commit -m "feat(room): seed Paco (boss, char_3+hue200, sofa-pref, conspiracy chat)"
```

---

### Task 4: Build final, dist, PR y deploy

**Files:**
- Modify: `room/dist/webview/**`

- [ ] **Step 1: Build limpio + tests**

Run: `cd room/webview-ui && npm run build && npm test`
Expected: build verde; tests PASS. Anotar el nuevo hash con
`grep -oE 'index-[A-Za-z0-9_-]+\.(js|css)' ../dist/webview/index.html`.

- [ ] **Step 2: Stage dist (SECUENCIAL)**

```bash
cd /mnt/data/repos/digital-observatory
git add room/dist/webview/index.html
git add room/dist/webview/assets/<nuevo-index>.js
git add room/dist/webview/assets/<viejo-index>.js   # captura el borrado
git ls-files --stage room/dist/webview/assets | grep -oE 'index-[A-Za-z0-9_-]+\.(js|css)'
```
(La CSS no cambia esta iteración salvo que cambie el hash; si cambia, añadir
ambos .css igual que el .js.)

- [ ] **Step 3: Commit dist + push**

```bash
git -C /mnt/data/repos/digital-observatory commit -m "build(room): dist for Paco agent (iteración D)"
git -C /mnt/data/repos/digital-observatory push origin room-ui-2
```

- [ ] **Step 4: PR**

```bash
gh pr create --base main --head room-ui-2 \
  --title "feat(room): agente Paco (jefe depre del sofá + frases conspiranoicas)" \
  --body "Nuevo 7º agente Paco (id 7): jefe (corona+glow), sprite char_3 + hueShift 200, arranca sentado en sofá si hay (findFreeSofaSeat) y a ratos deambula, suelta frases conspiranoico-depre cada ~8s. Reusa la maquinaria de iteraciones B/C. Sprite propio desde MetroCity queda fuera de alcance (incompatibilidad de formato 32×32 vs 16×32 sin poses type/read)."
```

- [ ] **Step 5: Merge (usuario) + deploy (con consentimiento explícito)**

```bash
ssh nano-spud 'cd /home/d3r/repos/digital-observatory && git pull --ff-only origin main && docker compose up -d --build observatory'
```

- [ ] **Step 6: Verificar (descarta caché)**

```bash
curl -sS http://100.84.156.15:8400/room/index.html | grep -oE 'index-[A-Za-z0-9_-]+\.js'   # == nuevo hash
curl -sS http://100.84.156.15:8400/room/assets/<nuevo-index>.js | grep -oE 'unabomber|ya fue|Paco' | sort -u
curl -sS -I http://100.84.156.15:8400/room/index.html | grep -i cache-control
```
Visual (incógnito + DevTools): aparece Paco (7º personaje) con nombre dorado + 👑,
sprite diferenciado; arranca sentado (sofá si hay) y a ratos deambula; suelta
frases conspiranoicas a su derecha cada ~8s.

---

## Notas de ejecución
- TDD aplica a Task 1. Resto: motor/UI verificado por build (TS estricto) + tests + visual.
- Git SECUENCIAL; borrar `.git/index.lock` si segfalla y verificar con `git status`.
- Si el layout no tiene sofás/bancas, `findFreeSofaSeat` devuelve null y Paco usa asiento normal (sin error).
- hueShift 200 es punto de partida, ajustable si Paco se ve raro o muy parecido a otro.
