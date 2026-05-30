# Diseño — Iteración D: agente Paco (jefe depre del sofá)

Fecha: 2026-05-30
Rama: room-ui-2
Alcance: **solo frontend** del cuarto (`room/webview-ui`). Sin backend. Mismo
pipeline build + deploy.

## Contexto

- El cuarto siembra su elenco en el frontend (`sseTransport` → `SEED_AGENTS` →
  `agentCreated` → `useExtensionMessages` → `addAgent` + `setAgentIdentity`).
- Iteración B añadió jefes (`isBoss` → corona 👑 + glow), wander idle, y nombres
  siempre visibles. Iteración C añadió paletas fijas por seed, bocadillos de chat
  periódicos (`chatLines`, `pickPhrase`, `ChatBubbleOverlay`) y el swap de sprites.
- Hay 6 sprites (`char_0..5`, 16×32, 7 frames, filas down/up/right). El motor de
  sprites es dinámico (`getLoadedCharacterCount`), pero **no agregamos sprite
  nuevo en esta iteración** (ver decisión).

## Decisión sobre el sprite (resultado de un spike)
Se intentó componer un sprite desde el pack MetroCity, pero el spike reveló
**incompatibilidad de formato**: MetroCity usa celdas 32×32, layout de 6 frames de
correr en 4 ejes, y **no trae poses de "escribir/leer"** que el motor requiere
(type0/1, read0) en celdas 16×32. Re-mapearlo implicaría re-escalar e inventar
frames, con alto riesgo de inconsistencia visual y muchas iteraciones a ciegas.

**Decisión del usuario:** Paco usa un **sprite existente con hue-shift propio**
(mismo patrón que Moreno). El sprite MetroCity queda como tarea de arte aparte
(cuando exista un `char_6.png` 112×96 en el formato del motor, se integra; fuera
de alcance aquí).

## Decisiones (confirmadas con el usuario)

1. **Paco** = nuevo agente, **id 7**, **jefe** (corona 👑 + glow dorado).
2. Sprite: `char_3` (claro/neutral, no usado por jefes) + **hueShift 200** para
   diferenciarlo. (Valor ajustable; no puedo verlo en vivo desde aquí.)
3. Comportamiento: **sentado + a veces deambula** (igual que Moreno: se siembra
   idle y usa el wander existente). Preferir un asiento de sofá/banca si el layout
   tiene uno libre; si no, asiento normal. No requiere animación de "acostado".
4. **Bocadillos de chat** periódicos (reusa iteración C): ≥8 frases conspiranoico/
   depre/financiero.

## Cambios por archivo

### `office/engine/chatLines.ts` — frases de Paco
Añadir:
```
PACO_LINES = [
  'ya fue',
  'el unabomber tenía razón',
  'todo está conectado, ¿no lo ves?',
  'mi peor decisión financiera fue existir',
  'nos están observando',
  'ya nada tiene sentido',
  'debí vender en el pico',
  'el sistema está diseñado para que pierdas',
]
```
(El helper `pickPhrase` ya existe y está testeado; solo se añade la lista.)

### `transport/eventTranslate.ts` — censo
- `AGENT_IDS.paco = 7`.
- Importar `PACO_LINES`.
- Añadir a `SEED_AGENTS`:
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
  }
  ```
- `SeedAgent` gana `preferSofa?: boolean`.

### `transport/sseTransport.ts` — siembra
- En el emit de `agentCreated`, pasar `preferSofa: a.preferSofa` (campo nuevo del
  mensaje). El resto (palette/hueShift/chatLines/isBoss) ya se propaga.
- Paco entra al loop de "marcar idle salvo el jugador" → deambula como Moreno.

### `core/src/messages.ts` — `AgentCreated`
- Añadir `preferSofa?: boolean`.

### `hooks/useExtensionMessages.ts` — preferencia de asiento
- En la rama no-teammate, si `msg.preferSofa`, resolver un `preferredSeatId` de un
  asiento cuyo mueble sea sofá/banca y esté libre, y pasarlo a
  `os.addAgent(id, palette, hueShift, preferredSeatId, …)`. Si no hay, `undefined`
  (asiento normal). Reusar el método de búsqueda de asientos de `officeState`
  (ver más abajo) en vez de duplicar lógica en el hook.

### `office/engine/officeState.ts` — buscar asiento de sofá
- Añadir `findFreeSofaSeat(): string | null` que recorra `this.seats`, mire el
  mueble dueño del asiento (`uid` → tipo de furniture) y devuelva el primero libre
  cuyo tipo sea de la familia sofá/banca (`SOFA`, `CUSHIONED_BENCH`,
  `WOODEN_BENCH`, `CUSHIONED_CHAIR`). Reutiliza el catálogo/layout ya disponible.
- El hook llama `os.findFreeSofaSeat()` cuando `preferSofa`.

> Nota: si el layout actual no tiene esos muebles, `findFreeSofaSeat` devuelve
> null y Paco usa asiento normal — comportamiento aceptable.

## Lógica nueva, aislada y testeable
- `PACO_LINES` ≥ 8 (test simple, junto a los de HESUS/MORENO).
- `findFreeSofaSeat` es lógica de motor con dependencias de layout; se valida por
  build + visual (no test unitario dedicado en esta iteración — YAGNI).

## Verificación
- `tsc -b && vite build` verde; tests PASS (incluye assert `PACO_LINES.length>=8`).
- Visual (incógnito + DevTools, hash nuevo): aparece Paco (7º personaje) con
  nombre dorado + 👑, sprite diferenciado (char_3 + hue 200); arranca sentado
  (sofá si hay) y a ratos deambula; suelta frases conspiranoicas a su derecha cada
  ~8s.

## Riesgos
- hueShift 200 es punto de partida; ajustable si se ve raro.
- Si char_3 queda muy parecido a otro tras el hue-shift, se distingue por nombre +
  corona.
- `findFreeSofaSeat` depende de que el layout tenga sofás/bancas; si no, fallback
  a asiento normal (sin error).

## Fuera de alcance (follow-up)
- Sprite propio de Paco desde MetroCity (requiere pipeline de arte: re-mapear
  32×32 → 16×32 e inventar poses type/read, o exportar un PNG ya en formato).
- Animación real de "acostado" en el sofá (el motor no la tiene).
- Moreno fact-checker backend.
