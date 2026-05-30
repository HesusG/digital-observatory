# Diseño — Iteración C: Moreno hombre (swap de sprites) + bocadillos de diálogo

Fecha: 2026-05-30
Rama: room-ui-2
Alcance: **solo frontend** del cuarto (`room/webview-ui`). Sin backend. Mismo
pipeline build + deploy.

## Contexto (verificado en el código)

- Hay **6 sprites** de personaje: `char_0..char_5` (`asset-index.json`). No hay
  metadata de género; el motor solo expone **hue-shift** (rotación de matiz), no
  brillo. Inspección visual: char_0 = hombre (camisa azul, pelo corto), char_4 =
  aspecto femenino (top blanco + falda azul).
- Las paletas se auto-asignan por orden de creación (`pickDiversePalette`): hoy
  tess=char_0, carla=char_1, edu=char_2, pablo=char_3, **moreno=char_4** (por eso
  Moreno se ve mujer), hesus=char_5.
- `addAgent(id, preferredPalette?, preferredHueShift?, …)` ya permite forzar
  paleta/hue. El mensaje `agentCreated` tiene campo `palette?`; falta `hueShift?`.
  La siembra ocurre en `transport/sseTransport.ts` (SEED_AGENTS → `agentCreated`)
  → `useExtensionMessages` (rama no-teammate, ~línea 191) → `os.addAgent(...)`.
- Los bocadillos actuales (`bubbleType: 'permission'|'waiting'`) son **iconos en
  canvas** (`renderer.ts::renderBubbles`), centrados ARRIBA del personaje. **No**
  hay render de texto en bocadillos.
- `ToolOverlay.tsx` posiciona elementos DOM sobre personajes con
  `deviceOffsetX/Y + ch.x*zoom` — patrón ideal para un bocadillo de texto a la
  derecha.

## Decisiones (confirmadas con el usuario)

1. **Isaac Moreno** (displayName se mantiene "Moreno"). Personalidad: creído
   financiero.
2. **Swap de sprites**: el sprite de hombre que hoy usa **tess (char_0)** pasa a
   **Moreno**, con un **hue-shift** para aclararlo/distinguirlo. El de mujer
   (char_4) pasa a **tess**.
   - Caveat aceptado: hue-shift rota el matiz, no es control de brillo; se aplica
     un valor moderado y queda ajustable.
3. **Bocadillos de diálogo periódicos** SOLO para Moreno y Hesus, a la **derecha**
   del personaje, **cada ~8s**, **duran ~3s**, frase **al azar** de su lista.
4. **≥8 frases por personaje** (Hesus miedoso; Moreno creído financiero).

## Cambios por archivo

### Paletas fijas (swap)
- `transport/eventTranslate.ts` — `SeedAgent` gana `palette?: number` y
  `hueShift?: number`; en `SEED_AGENTS`:
  - tess: `palette: 4`
  - carla: `palette: 1`, edu: `palette: 2`, pablo: `palette: 3`, hesus: `palette: 5`
  - moreno: `palette: 0, hueShift: 35`
- `core/src/messages.ts` — `AgentCreated` gana `hueShift?: number` (ya tiene
  `palette?`).
- `transport/sseTransport.ts` — en el emit de `agentCreated`, pasar
  `palette: a.palette` y `hueShift: a.hueShift`.
- `hooks/useExtensionMessages.ts` — en la rama no-teammate, leer `msg.palette` y
  `msg.hueShift` y pasarlos a `os.addAgent(id, palette, hueShift, …)`.

### Frases (data)
Añadir en el nuevo módulo `office/engine/chatLines.ts`:
```
HESUS_LINES = ['Si bro!', 'tengo miedo', '¿crees que me vaya a morir?',
  '¿y si truena el servidor?', 'no me dejes solo bro',
  'esto se va a caer, lo sé', '¿viste eso? qué miedo',
  '¿seguro que esto es seguro?']
MORENO_LINES = ['uff!', 'medio día', 'el mercado nunca duerme',
  'yo ya lo había predicho', 'eso es ruido, no señal',
  'mis valuaciones nunca fallan', 'esto es alfa puro',
  'los amateurs venden, yo acumulo']
```
Y un helper puro `pickPhrase(lines, prevIndex): { text, index }` que elige un
índice al azar evitando repetir `prevIndex` (si la lista tiene ≥2). La aleatoriedad
usa `Math.random()` en runtime; el TEST inyecta un `rand` opcional para ser
determinista: `pickPhrase(lines, prevIndex, rand?)`.

### Estado + timing (motor)
- `office/types.ts` — `Character` gana:
  - `chatLines?: string[]` — frases de este personaje (solo Moreno/Hesus).
  - `chatText: string | null` — frase visible ahora (o null).
  - `chatTimer: number` — cuenta regresiva (visible) o cooldown (oculto).
  - `chatPrevIndex: number` — última frase mostrada (para no repetir).
  - Inicializar en `createCharacter` (`chatText:null, chatTimer:`cooldown inicial
    aleatorio`, chatPrevIndex:-1`).
- `constants.ts` — `CHAT_BUBBLE_VISIBLE_SEC = 3`, `CHAT_BUBBLE_GAP_MIN_SEC = 7`,
  `CHAT_BUBBLE_GAP_MAX_SEC = 10` (≈ "cada ~8s").
- `office/engine/officeState.ts`:
  - `setAgentIdentity` acepta `chatLines?` y lo asigna.
  - En `update(dt)`, por personaje con `chatLines`: si `chatText` visible, restar
    dt hasta 0 → ocultar y poner `chatTimer = gap aleatorio`; si oculto, restar dt
    hasta 0 → `pickPhrase` y mostrar (`chatTimer = CHAT_BUBBLE_VISIBLE_SEC`). El
    jugador (Hesus) también habla aunque lo controles con WASD.
- `transport/eventTranslate.ts` — `SeedAgent` gana `chatKey?: 'hesus'|'moreno'`;
  `sseTransport` pasa las líneas correspondientes vía `agentCreated`
  (`chatLines?: string[]`) → `useExtensionMessages` → `setAgentIdentity`.
  (`core/src/messages.ts` `AgentCreated` gana `chatLines?: string[]`.)

### Render del bocadillo de texto (DOM)
- Nuevo `office/components/ChatBubbleOverlay.tsx` (patrón de `ToolOverlay`):
  recorre los personajes con `ch.chatText`, calcula `screenX/screenY` igual que
  ToolOverlay y posiciona un globo **a la derecha** (`left: screenX + offsetPx`,
  centrado verticalmente en la cabeza). Estilo `pixel-panel`, texto pequeño,
  `whitespace-nowrap`, `pointer-events-none`, pico/tail opcional. Se monta en
  `App.tsx` junto a `ToolOverlay` (mismos props: `officeState`, `agents`,
  `containerRef`, `zoom`, `panRef`).

## Lógica nueva, aislada y testeable
- `chatLines.ts::pickPhrase(lines, prevIndex, rand?)` — helper puro; tests
  `node:test`: (a) nunca repite `prevIndex` con lista ≥2; (b) con lista de 1
  devuelve índice 0; (c) respeta `rand` inyectado.

## Verificación
- `tsc -b && vite build` verde; tests PASS.
- Visual (incógnito + DevTools, hash nuevo): Moreno se ve hombre (sprite char_0
  con hue-shift), tess con char_4; cada ~8s Moreno y Hesus muestran una frase a su
  derecha ~3s; frases rotan sin repetir la inmediata; no aplican a workers.

## Riesgos
- hue-shift no aclara linealmente; el valor 35 es punto de partida ajustable.
- Si dos sprites quedan idénticos tras el swap, distinguirlos por nombre/corona
  (ya implementado en iteración B).
- `Math.random` no es testeable directo → helper acepta `rand` inyectable.

## Fuera de alcance (follow-up)
- Moreno fact-checker backend (eventos `moreno.*`).
- Burbujas reactivas a eventos reales (hoy son ambientales/fijas).
