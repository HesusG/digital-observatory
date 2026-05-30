# Diseño — Iteración B: Moreno + Hesus (jefes), nombres con glow, wander idle, WASD

Fecha: 2026-05-30
Rama: room-ui-2
Alcance: **solo frontend** del cuarto (`room/webview-ui`). Sin cambios de backend
(la lógica del fact-checker Moreno sigue diferida). Mismo pipeline build + deploy.

## Contexto (verificado en el código)

- El cuarto usa **SSE** en modo navegador. Los 4 workers (tess/carla/edu/pablo)
  **se siembran en el frontend** al conectar: `transport/sseTransport.ts` emite un
  `agentCreated` por cada uno usando `AGENT_IDS`/`AGENT_ORDER` de
  `transport/eventTranslate.ts`. Por eso aparecen en producción.
- Los eventos de `/api/events` se traducen (`eventTranslate.ts`) a mensajes
  `agentStatus` + herramientas que animan a esos 4. `agentStatus` con estado ≠
  `active` pone `isActive=false`, que **dispara el wander idle ya existente**
  (`office/engine/characters.ts`, estado IDLE).
- **Hoy no se muestran nombres** sobre los personajes: el label de nombre en
  `office/components/ToolOverlay.tsx` solo aparece para team leads/teammates
  (`agentName`/`isTeamLead`). Los workers solo muestran su actividad.
- Los personajes arrancan `isActive=true` (escribiendo). Como no siempre llega un
  evento que los marque inactivos, "muchas veces están escribiendo" y no caminan.
- **No existe** `isPlayer` ni control WASD.

## Decisiones (confirmadas con el usuario)

1. **Hesus** = jugador controlado con **WASD** y además se ve como jefe.
2. **Moreno** = jefe NPC que deambula solo (solo personaje del cuarto por ahora).
3. **Nombres**: todos muestran etiqueta de nombre; workers en estilo normal,
   **Moreno y Hesus con nombre dorado + glow + 👑** (sin cambiar el sprite).
4. **Wander idle**: workers deambulan cuando no procesan eventos, y Moreno también.
   Hesus NO deambula (es jugador).

## Enfoques elegidos

- **Siembra de jefes en el frontend** (`sseTransport.ts`), no en el backend.
- **Movimiento WASD por paso de tile**: cada tecla encola un movimiento de una
  casilla reusando el sistema WALK + lerp + chequeo de tile caminable; mantener la
  tecla sigue avanzando. (No movimiento libre por píxel.)

## Cambios por archivo

### `src/office/types.ts` — modelo
Agregar a `Character` (opcionales, no rompen el resto):
- `isBoss?: boolean` — activa glow + 👑 en el nombre.
- `isPlayer?: boolean` — control WASD (solo Hesus).

`agentName` ya existe y se reutiliza para el nombre de los jefes.

### `src/transport/eventTranslate.ts` — censo de personajes
Extender el censo con los dos jefes (IDs nuevos que no chocan con 1–4):
- `moreno` → id 5, `hesus` → id 6.
- Añadir un mapa de metadatos para la siembra, p.ej.
  `SEED_AGENTS: Array<{ name, id, isBoss?, isPlayer? }>` que incluya a los 4
  workers (sin flags) + moreno (`isBoss`) + hesus (`isBoss`,`isPlayer`).

### `src/transport/sseTransport.ts` — siembra + arranque idle
- Emitir `agentCreated` para los 6 (workers + jefes) con los campos nuevos
  (`displayName`, `isBoss`, `isPlayer`) tomados de `SEED_AGENTS`.
- Tras sembrar, emitir `agentStatus` **inactivo** para todos excepto Hesus, de
  modo que entren a IDLE y deambulen con el wander existente. Los eventos los
  reactivan cuando trabajan.

### `src/hooks/useExtensionMessages.ts` — propagar flags
- En el handler de `agentCreated`, leer los campos opcionales `displayName`,
  `isBoss`, `isPlayer` y aplicarlos al `Character` recién creado (vía un método de
  `officeState`, ver abajo). Mantener compatibilidad con VS Code (campos
  ausentes → sin cambios).

### `src/office/engine/officeState.ts` — setters + input de jugador
- `addAgent(...)` o un nuevo método `setAgentIdentity(id, { displayName?, isBoss?, isPlayer? })`
  para fijar `agentName`/`isBoss`/`isPlayer` después de crear el personaje.
- Para el jugador: spawnear sin asiento (roam libre) o liberar su asiento; fijar
  `cameraFollowId` al id del jugador para que la cámara lo siga.
- Estado de input del jugador: `playerInput = { up, down, left, right }` (campo en
  `OfficeState`), leído por `update(dt)` para el personaje `isPlayer`.

### `src/office/engine/characters.ts` — WASD + saltar IA del jugador
- En `updateCharacter`, si `ch.isPlayer`:
  - No ejecutar la lógica de wander/IDLE/TYPE automática.
  - Si `ch.path` está vacío y hay alguna tecla activa, calcular el tile vecino en
    esa dirección; si es caminable (misma función de caminabilidad que usa el
    pathfinding), encolar ese paso (`ch.path = [tileVecino]`, `state = WALK`).
    Si no es caminable, solo orientar `ch.dir` (para que mire hacia allá).
  - El resto del movimiento (lerp) lo maneja el caso WALK existente.

### `src/hooks/usePlayerControls.ts` — input WASD (nuevo)
- `useEffect` que registra keydown/keyup para W/A/S/D (y flechas, opcional) y
  actualiza `officeState.playerInput`. Se desactiva si `isEditMode` está activo o
  si el foco está en un input/textarea (evitar capturar escritura). Limpia
  listeners al desmontar. Se monta desde `App.tsx`.

### `src/office/components/ToolOverlay.tsx` + `src/constants.ts` — nombres + glow
- Nombre a mostrar: `ch.agentName ?? ch.folderName ?? (ch.isTeamLead ? 'LEAD' : null)`.
- Si `ch.isBoss`: color `BOSS_NAME_COLOR`, `fontWeight:'bold'`,
  `textShadow: BOSS_NAME_GLOW`, y prefijo `👑 ` antes del nombre.
- `constants.ts`: `BOSS_NAME_COLOR = '#ffd700'` y
  `BOSS_NAME_GLOW = '0 0 6px rgba(255,215,0,0.9), 0 0 14px rgba(255,170,0,0.5)'`.

## Lógica nueva, aislada y testeable

Helper puro (sin DOM ni React), p.ej. en `office/engine/playerMove.ts`:
- `stepTile(col, row, dir): { col, row }` — tile vecino en una dirección.
- (Reusar la función de caminabilidad existente del motor para validar; el helper
  puro solo calcula el vecino y se testea con `node:test`.)

## Verificación
- `tsc -b && vite build` verde.
- Unit test de `stepTile` (las 4 direcciones, desde un tile dado).
- Visual (incógnito + DevTools confirmando hash): aparecen 6 personajes; Moreno y
  Hesus con nombre dorado + glow + 👑; los workers muestran su nombre; los workers
  y Moreno deambulan cuando están idle; Hesus se mueve con WASD y la cámara lo
  sigue; WASD no interfiere con el modo edición.

## Riesgos
- WASD podría capturar teclas en inputs/edición → mitigado desactivando el hook en
  esos casos.
- IDs 5/6 de los jefes no deben colisionar con sub-agentes; los sub-agentes usan
  su propio rango — verificar al implementar.
- Marcar agentes como inactivos al arranque cambia el comportamiento inicial
  (antes "escribiendo"); es justo lo deseado (deambular en reposo).

## Fuera de alcance (follow-up)
- **Moreno fact-checker backend** (orquestador, prompts, eventos `moreno.*`).
