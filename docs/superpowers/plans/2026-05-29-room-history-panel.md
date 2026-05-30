# Room History Panel (Iteración A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mejorar el panel de historial del cuarto (ancho 400, chips por agente, franjas mañana/tarde/noche colapsables), mover el botón ℹ️ a arriba-derecha, restaurar solo el botón Layout, y subir ~12% la fuente global.

**Architecture:** Solo frontend de `room/webview-ui`. La lógica de agrupado (franja/día en hora local) se extrae a un módulo puro DOM-free (`historyGrouping.ts`) para poder testearla con `node:test`. `HistoryLog.tsx` consume esos helpers y maneja estado de filtro (chips) y colapso. Sin cambios de backend ni del motor/canvas.

**Tech Stack:** React 19, TypeScript, Tailwind v4 (`--spacing:1px`, tamaños de texto en px), Vite, `node --test` + `tsx`.

---

### Task 1: Helpers puros de agrupado + tests

**Files:**
- Create: `room/webview-ui/src/components/historyGrouping.ts`
- Test: `room/webview-ui/test/historyGrouping.test.ts`

- [ ] **Step 1: Write the failing test**

`room/webview-ui/test/historyGrouping.test.ts`:
```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd room/webview-ui && npm test`
Expected: FAIL — `Cannot find module '../src/components/historyGrouping.ts'`.

- [ ] **Step 3: Write minimal implementation**

`room/webview-ui/src/components/historyGrouping.ts`:
```ts
// Pure, DOM-free helpers for grouping history events by LOCAL day and time band.
// Kept separate from HistoryLog.tsx so they can be unit-tested with node:test.

export type Band = 'manana' | 'tarde' | 'noche';

export const BAND_ORDER: Band[] = ['manana', 'tarde', 'noche'];

export const BAND_LABEL: Record<Band, string> = {
  manana: '🌅 Mañana',
  tarde: '☀️ Tarde',
  noche: '🌙 Noche',
};

// Local hour bands: Mañana [6,12), Tarde [12,19), Noche [19,24) ∪ [0,6).
export function bandOf(date: Date): Band {
  const h = date.getHours();
  if (h >= 6 && h < 12) return 'manana';
  if (h >= 12 && h < 19) return 'tarde';
  return 'noche';
}

// Local YYYY-MM-DD (not UTC) so day boundaries match the viewer's clock.
export function localDayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// Local HH:MM.
export function localTimeLabel(date: Date): string {
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function groupKey(day: string, band: Band): string {
  return `${day}|${band}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd room/webview-ui && npm test`
Expected: PASS (all `historyGrouping` tests + the existing `dev-assets` tests).

- [ ] **Step 5: Commit**

```bash
git add room/webview-ui/src/components/historyGrouping.ts room/webview-ui/test/historyGrouping.test.ts
git commit -m "feat(room): pure local-time day/band grouping helpers + tests"
```

---

### Task 2: Fuente global +~12% (`index.css`)

**Files:**
- Modify: `room/webview-ui/src/index.css:56-65` (los tokens `--text-*`)

- [ ] **Step 1: Edit the text tokens**

Reemplazar el bloque de tamaños (líneas que hoy dicen `--text-2xs: 16px;` … `--text-5xl: 64px;`) por:
```css
  /* Text sizes (pixel-art scale, base = 25px ≈ +12% sobre 22px) */
  --text-*: initial;
  --text-2xs: 18px;
  --text-xs: 20px;
  --text-sm: 22px;
  --text-base: 25px;
  --text-lg: 29px;
  --text-xl: 34px;
  --text-2xl: 40px;
  --text-3xl: 50px;
  --text-4xl: 58px;
  --text-5xl: 72px;
```

- [ ] **Step 2: Verify build is green**

Run: `cd room/webview-ui && npm run build`
Expected: `tsc -b && vite build` sin errores; emite `../dist/webview/assets/index-*.css`.

- [ ] **Step 3: Commit**

```bash
git add room/webview-ui/src/index.css
git commit -m "feat(room): bump global font sizes ~12%"
```

> El commit del `dist` se hace junto con todo en la Task 6 (build final único).

---

### Task 3: Botón ℹ️ a arriba-derecha (`InfoButton.tsx`)

**Files:**
- Modify: `room/webview-ui/src/components/InfoButton.tsx:11-19`

- [ ] **Step 1: Move the button to top-right**

Reemplazar el `<button>` por:
```tsx
      <button
        onClick={() => setOpen(true)}
        // Explicit px: this app's Tailwind sets --spacing:1px. Top-right of the
        // office area so it doesn't collide with the zoom controls (top-left).
        className="absolute z-30 pixel-panel flex items-center justify-center text-2xl cursor-pointer hover:text-accent-bright"
        style={{ top: 16, right: 16, width: 44, height: 44 }}
        title="¿Qué es esto?"
      >
        ℹ️
      </button>
```

Y actualizar el comentario superior del archivo:
```tsx
// Small "ℹ️" button (top-right of the office) that explains the project.
```

- [ ] **Step 2: Verify build is green**

Run: `cd room/webview-ui && npm run build`
Expected: build verde.

- [ ] **Step 3: Commit**

```bash
git add room/webview-ui/src/components/InfoButton.tsx
git commit -m "feat(room): move info button to top-right"
```

---

### Task 4: Restaurar solo el botón Layout (`BottomToolbar.tsx`)

**Files:**
- Modify: `room/webview-ui/src/components/BottomToolbar.tsx` (reemplazo total del archivo)

- [ ] **Step 1: Replace the file with a Layout-only toolbar**

`room/webview-ui/src/components/BottomToolbar.tsx`:
```tsx
import type { WorkspaceFolder } from '../hooks/useExtensionMessages.js';
import { Button } from './ui/Button.js';

interface BottomToolbarProps {
  isEditMode: boolean;
  onOpenClaude: () => void;
  onToggleEditMode: () => void;
  isSettingsOpen: boolean;
  onToggleSettings: () => void;
  workspaceFolders: WorkspaceFolder[];
}

// Read-only public room: expose ONLY the "Layout" toggle (customize the office).
// +Agent and Settings are intentionally not rendered. Only the two props this
// component uses are destructured; the rest remain in the interface (App.tsx
// still passes them) so there are no unused locals at the call site, and
// noUnusedParameters is satisfied because undestructured props don't count.
export function BottomToolbar({ isEditMode, onToggleEditMode }: BottomToolbarProps) {
  return (
    <div className="absolute bottom-10 left-10 z-20 flex items-center gap-4 pixel-panel p-4">
      <Button
        variant={isEditMode ? 'active' : 'default'}
        onClick={onToggleEditMode}
        title="Edit office layout"
      >
        Layout
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Verify build is green (catches unused locals/params)**

Run: `cd room/webview-ui && npm run build`
Expected: build verde (sin errores TS6133 de unused).

- [ ] **Step 3: Commit**

```bash
git add room/webview-ui/src/components/BottomToolbar.tsx
git commit -m "feat(room): restore Layout-only bottom toolbar"
```

---

### Task 5: Reescribir `HistoryLog.tsx` (400px, chips, franjas colapsables)

**Files:**
- Modify: `room/webview-ui/src/components/HistoryLog.tsx` (reemplazo total)

> `HISTORY_PANEL_WIDTH` se exporta desde aquí y App.tsx ya lo importa para el
> inset de la oficina; subirlo a 400 ajusta panel y oficina sin tocar App.tsx.

- [ ] **Step 1: Replace the file**

`room/webview-ui/src/components/HistoryLog.tsx`:
```tsx
import { useEffect, useMemo, useRef, useState } from 'react';

import { BAND_LABEL, BAND_ORDER, bandOf, groupKey, localDayKey, localTimeLabel } from './historyGrouping.js';
import type { Band } from './historyGrouping.js';

// Always-visible right-side panel showing the day's agent activity, read
// straight from the observatory event log (GET /api/events + SSE stream).
//
// NOTE: this app's Tailwind (v4) sets `--spacing: 1px` in index.css, so a class
// like `w-80` is 80px, NOT 320px. The panel's structural width is an explicit
// pixel constant used by inline style here AND by App.tsx to inset the office.
export const HISTORY_PANEL_WIDTH = 400;

interface ApiEvent {
  seq: number;
  ts: string;
  agent: string;
  event_type: string;
  payload?: Record<string, unknown> | null;
  platform?: string | null;
  lang?: string | null;
}

const AGENT_EMOJI: Record<string, string> = {
  tess: '🔭',
  carla: '✍️',
  edu: '📐',
  pablo: '📤',
  user: '👤',
};

// Order of the filter chips. Known agents; unknown agents are always shown.
const AGENTS = ['tess', 'carla', 'edu', 'pablo', 'user'];
const KNOWN_AGENTS = new Set(AGENTS);

function clip(v: unknown, n = 46): string {
  const s = String(v ?? '');
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function describe(ev: ApiEvent): string {
  const p = ev.payload ?? {};
  const pl = ev.platform ? ` ${ev.platform}` : '';
  switch (ev.event_type) {
    case 'tess.scored':
      return `puntuó “${clip(p.title, 32)}” (${String(p.teacher_relevance ?? '?')}/10)`;
    case 'tess.skipped':
      return `descartó: ${clip(p.skip_reason)}`;
    case 'carla.drafted':
      return `redactó${pl}/${ev.lang ?? ''}`;
    case 'edu.approved':
      return `aprobó${pl} ✅`;
    case 'edu.revise':
      return `pidió revisión: ${clip(p.reasoning, 30)}`;
    case 'edu.reject':
      return `rechazó: ${clip(p.reasoning, 30)}`;
    case 'pablo.published':
      return `publicó${pl} 🚀`;
    case 'pablo.failed':
      return `falló al publicar: ${clip(p.error, 28)}`;
    case 'user.approved':
      return `aprobaste un borrador`;
    case 'user.skipped':
      return `omitiste un borrador`;
    default:
      return ev.event_type;
  }
}

interface BandGroup {
  band: Band;
  key: string;
  events: ApiEvent[];
}
interface DayGroup {
  day: string;
  bands: BandGroup[];
}

// Group events (assumed sorted by seq asc) into day -> band, in local time.
function groupByDayBand(events: ApiEvent[]): DayGroup[] {
  const days = new Map<string, Map<Band, ApiEvent[]>>();
  for (const ev of events) {
    const d = new Date(ev.ts);
    const day = localDayKey(d);
    const band = bandOf(d);
    let bands = days.get(day);
    if (!bands) {
      bands = new Map<Band, ApiEvent[]>();
      days.set(day, bands);
    }
    const arr = bands.get(band);
    if (arr) arr.push(ev);
    else bands.set(band, [ev]);
  }
  return [...days.keys()]
    .sort()
    .map((day) => ({
      day,
      bands: BAND_ORDER.filter((b) => days.get(day)!.has(b)).map((band) => ({
        band,
        key: groupKey(day, band),
        events: days.get(day)!.get(band)!,
      })),
    }));
}

export function HistoryLog() {
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const seenRef = useRef<Set<number>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);

  // Agent filter: set of ACTIVE agents (all on by default).
  const [activeAgents, setActiveAgents] = useState<Set<string>>(() => new Set(AGENTS));
  // Collapse overrides per group key; default-open rule is `day === today`.
  const [openOverride, setOpenOverride] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    function add(incoming: ApiEvent[]) {
      const fresh = incoming.filter((e) => !seenRef.current.has(e.seq));
      if (fresh.length === 0) return;
      fresh.forEach((e) => seenRef.current.add(e.seq));
      setEvents((prev) => [...prev, ...fresh].sort((a, b) => a.seq - b.seq));
    }

    (async () => {
      try {
        const res = await fetch('/api/events?since_seq=0&limit=500');
        const data = (await res.json()) as { events?: ApiEvent[]; latest_seq?: number };
        if (cancelled) return;
        add(data.events ?? []);
        const last = data.latest_seq ?? 0;
        es = new EventSource(`/api/events/stream?since_seq=${last}`);
        es.onmessage = (e: MessageEvent) => {
          try {
            add([JSON.parse(e.data as string) as ApiEvent]);
          } catch {
            /* ignore malformed */
          }
        };
      } catch {
        /* offline; panel stays empty */
      }
    })();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, []);

  const visibleEvents = useMemo(
    () => events.filter((e) => !KNOWN_AGENTS.has(e.agent) || activeAgents.has(e.agent)),
    [events, activeAgents],
  );
  const dayGroups = useMemo(() => groupByDayBand(visibleEvents), [visibleEvents]);
  const todayKey = localDayKey(new Date());

  // Auto-scroll to the newest entry when events change.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visibleEvents]);

  function toggleAgent(agent: string) {
    setActiveAgents((prev) => {
      const next = new Set(prev);
      if (next.has(agent)) next.delete(agent);
      else next.add(agent);
      return next;
    });
  }

  function isOpen(day: string, key: string): boolean {
    return openOverride[key] ?? day === todayKey;
  }
  function toggleGroup(day: string, key: string) {
    const current = isOpen(day, key);
    setOpenOverride((prev) => ({ ...prev, [key]: !current }));
  }

  return (
    <div
      className="absolute top-0 right-0 bottom-0 z-20 pixel-panel flex flex-col border-l-2 border-border"
      style={{ width: HISTORY_PANEL_WIDTH }}
    >
      <div className="px-12 py-8 text-lg text-accent-bright border-b border-border shrink-0">
        📋 Historial del día
      </div>

      {/* Agent filter chips */}
      <div className="px-10 py-6 flex flex-wrap gap-3 border-b border-border shrink-0">
        {AGENTS.map((agent) => {
          const on = activeAgents.has(agent);
          return (
            <button
              key={agent}
              onClick={() => toggleAgent(agent)}
              title={on ? `Ocultar ${agent}` : `Mostrar ${agent}`}
              className={
                'pixel-panel px-6 py-2 text-sm cursor-pointer flex items-center gap-2 ' +
                (on ? 'text-text' : 'opacity-40')
              }
            >
              <span>{AGENT_EMOJI[agent] ?? '•'}</span>
              <span className="text-accent-bright">{agent}</span>
            </button>
          );
        })}
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto px-10 py-8 flex flex-col gap-3">
        {dayGroups.length === 0 && (
          <div className="text-sm opacity-50">Sin actividad todavía…</div>
        )}
        {dayGroups.map((dg) => (
          <div key={dg.day} className="flex flex-col gap-2">
            <div className="text-sm text-accent-bright opacity-80 mt-4 mb-1">{dg.day}</div>
            {dg.bands.map((bg) => {
              const open = isOpen(dg.day, bg.key);
              return (
                <div key={bg.key} className="flex flex-col">
                  <button
                    onClick={() => toggleGroup(dg.day, bg.key)}
                    className="flex items-center gap-3 text-sm text-text py-2 cursor-pointer select-none hover:text-accent-bright"
                  >
                    <span className="opacity-70 w-8 inline-block">{open ? '▾' : '▸'}</span>
                    <span>{BAND_LABEL[bg.band]}</span>
                    <span className="opacity-40">({bg.events.length})</span>
                  </button>
                  {open && (
                    <div className="flex flex-col gap-3 pl-10 pb-2">
                      {bg.events.map((ev) => (
                        <div key={ev.seq} className="text-sm leading-snug flex gap-4">
                          <span className="opacity-40 shrink-0">
                            {localTimeLabel(new Date(ev.ts))}
                          </span>
                          <span>
                            <span className="mr-2">{AGENT_EMOJI[ev.agent] ?? '•'}</span>
                            <span className="text-accent-bright">{ev.agent}</span> {describe(ev)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build is green**

Run: `cd room/webview-ui && npm run build`
Expected: build verde; nuevo `index-*.js` / `index-*.css`.

- [ ] **Step 3: Run unit tests (helpers still green)**

Run: `cd room/webview-ui && npm test`
Expected: PASS.

- [ ] **Step 4: Commit (source only)**

```bash
git add room/webview-ui/src/components/HistoryLog.tsx
git commit -m "feat(room): history panel 400px + agent chips + collapsible day/band groups"
```

---

### Task 6: Build final, dist, PR y deploy

**Files:**
- Modify: `room/dist/webview/**` (artefacto de build, commiteado)

- [ ] **Step 1: Build limpio final**

Run: `cd room/webview-ui && npm run build`
Expected: build verde; anotar el nuevo hash `index-*.js` de `room/dist/webview/index.html`.

- [ ] **Step 2: Stage dist en trozos (evita el segfault intermitente de `git add room/dist`)**

```bash
cd /mnt/data/repos/digital-observatory
git add room/dist/webview/index.html
git add room/dist/webview/assets/<nuevo-index>.js
git add room/dist/webview/assets/<nuevo-index>.css
git add -A room/dist/webview/assets   # recoge borrados de los hashes viejos
git ls-tree -r HEAD --name-only room/dist/webview/assets | grep index-   # verificar consistencia
```

- [ ] **Step 3: Commit dist + push**

```bash
git commit -m "build(room): dist for history panel iteration A"
git push origin room-ui-2
```

- [ ] **Step 4: PR**

```bash
gh pr create --base main --head room-ui-2 \
  --title "feat(room): history panel iteración A (chips, franjas, fuente, info, Layout)" \
  --body "Panel 400px + chips por agente + franjas mañana/tarde/noche colapsables (hora local), ℹ️ arriba-derecha, botón Layout restaurado, fuente global +12%. Helpers de agrupado con tests (node:test)."
```

- [ ] **Step 5: Merge (usuario) + deploy (con consentimiento explícito)**

En nano-spud (requiere autorización del usuario para el deploy de producción):
```bash
ssh nano-spud 'cd /home/d3r/repos/digital-observatory && git pull --ff-only origin main && docker compose up -d --build observatory'
```

- [ ] **Step 6: Verificar (descarta caché)**

```bash
curl -sS http://100.84.156.15:8400/room/index.html | grep -o 'index-[A-Za-z0-9_]*\.js'   # == nuevo hash
curl -sS -I http://100.84.156.15:8400/room/index.html | grep -i cache-control             # no-cache
```
Visual (usuario, incógnito + DevTools): panel 400px, chips togglean, franjas plegables (hoy abierto), ℹ️ arriba-derecha, botón Layout abajo-izq entra a edición, letra más grande.

---

## Notas de ejecución
- TDD solo aplica a Task 1 (lógica pura). El resto es UI: se verifica con `npm run build` (TS estricto: `noUnusedLocals`/`noUnusedParameters`) y revisión visual.
- No tocar `App.tsx`: ya importa `HISTORY_PANEL_WIDTH`; subirlo a 400 en `HistoryLog.tsx` ajusta panel y oficina.
- `SettingsModal` queda montado sin punto de acceso (UI muerta de bajo riesgo, aceptado en el spec).
