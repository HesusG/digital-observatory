# Diseño — Iteración A: panel de historial + chrome del cuarto + fuente

Fecha: 2026-05-29
Rama: room-ui-2
Alcance: **solo frontend** del cuarto (`room/webview-ui`). Sin cambios de backend ni
del motor/canvas. Mismo pipeline build + deploy.

## Contexto

El cuarto (`/room`, fork de pixel-agents servido por el observatory) ya tiene la
maquetación arreglada (panel de 320px a la derecha + oficina a la izquierda; ver
`2026-05-29` fix de `--spacing:1px`). Esta iteración mejora el panel de historial
y el chrome, según feedback del usuario.

Datos relevantes:
- Agentes del log: `tess` 🔭, `carla` ✍️, `edu` 📐, `pablo` 📤, `user` 👤
  (`AGENT_EMOJI` en `HistoryLog.tsx`).
- Los eventos traen `ts` ISO **UTC**; el panel los lee de `/api/events` + SSE.
- Tailwind v4: `--spacing: 1px` (spacing en px) y tamaños de texto fijos en px en
  `@theme` (`--text-base: 22px`, etc.) — NO son `rem`.
- Controles de zoom en `top-8 left-8` (arriba-izq); título centrado arriba
  (`VersionIndicator`/`ZoomControls`). Por eso el ℹ️ en arriba-izq chocaba.

## Objetivos (confirmados con el usuario)

1. **ℹ️ arriba-derecha** del área de oficina (deja de chocar con zoom).
2. **Panel de historial más ancho**: 320 → **400px**.
3. **Agrupar por Día → Franja** (Mañana/Tarde/Noche), **colapsable**.
4. **Filtrable por agente** mediante chips toggle.
5. **Letra global ~12% más grande** (todo el texto; el canvas no cambia).
6. **Restaurar solo el botón "Layout"** (personalizar el cuarto) en abajo-izq.
   El botón Settings y +Agent quedan fuera; `SettingsModal` sigue montado pero
   sin punto de acceso.

Fuera de alcance (follow-ups, solo opinión por ahora):
- **B**: actividades variadas de agentes idle (motor/animación).
- **C**: nuevo agente **Moreno** (fact-checker de finanzas IA / geopolítica /
  valuaciones) — backend + personaje; spec propio.

## Cambios por archivo

### `src/index.css` — fuente global (+~12%)
Escalar los tokens `--text-*` (redondeo a px):

| token | antes | después |
|---|---|---|
| 2xs | 16 | 18 |
| xs  | 18 | 20 |
| sm  | 20 | 22 |
| base| 22 | 25 |
| lg  | 26 | 29 |
| xl  | 30 | 34 |
| 2xl | 36 | 40 |
| 3xl | 44 | 50 |
| 4xl | 52 | 58 |
| 5xl | 64 | 72 |

Cambio aislado; si algún componente se aprieta, se ajusta el token puntual.

### `src/components/InfoButton.tsx` — arriba-derecha
`style={{ top: 16, left: 16, ... }}` → `style={{ top: 16, right: 16, width: 44, height: 44 }}`.
Sigue siendo hijo del área de oficina (en `App.tsx`), así que "right:16" lo pega
al borde interno del panel. Mantiene 44×44 y el modal explicativo.

### `src/components/HistoryLog.tsx` — el grueso
- **Ancho**: `HISTORY_PANEL_WIDTH = 400` (App.tsx ya lo importa para el inset).
- **Chips de agente**: fila bajo el encabezado con un chip por agente
  (emoji + nombre). Estado `Set<string>` de agentes **activos**; por defecto
  todos activos. Click togglea; chip inactivo = atenuado (opacity) y sus eventos
  se ocultan. Filtro se aplica antes de agrupar.
- **Agrupado Día → Franja** en **hora local del navegador** (`new Date(ts)`):
  - 🌅 **Mañana** `[6, 12)`
  - ☀️ **Tarde** `[12, 19)`
  - 🌙 **Noche** `[19, 24) ∪ [0, 6)`
  - Orden cronológico ascendente (día asc; dentro del día Mañana→Tarde→Noche;
    dentro de franja por `seq`). Lo más nuevo abajo; se mantiene el auto-scroll
    al final cuando llegan eventos.
  - Solo se dibujan franjas con ≥1 evento tras el filtro de chips.
- **Colapsable por franja**: cada encabezado de franja tiene chevron ▸/▾.
  - Clave de grupo: `${día}|${franja}`.
  - Estado abierto: `override[clave] ?? (día === hoyLocal)` → **hoy expandido,
    días anteriores plegados**, respetando lo que el usuario toque. `override`
    es `Record<string, boolean>` solo para claves tocadas (robusto ante grupos
    nuevos que llegan por SSE).
- Encabezado "📋 Historial del día" se mantiene.

### `src/App.tsx`
- `HISTORY_PANEL_WIDTH` pasa a 400 (definido en `HistoryLog.tsx`); el inset de la
  oficina (`style={{ right: HISTORY_PANEL_WIDTH }}`) se ajusta solo.
- El ℹ️ sigue como hijo del área de oficina (ahora arriba-derecha).
- Sin cambios de props: el `BottomToolbar` conserva su interfaz; App sigue
  pasándole las mismas props (evita unused-locals).

### `src/components/BottomToolbar.tsx` — restaurar solo "Layout"
- Volver a renderizar (ya no `null`), pero **solo el botón Layout**
  (`onToggleEditMode` / `isEditMode`) en abajo-izquierda (`absolute bottom-10
  left-10`, antes colisionaba con el ℹ️ que ahora está arriba-derecha).
- Quitar del render: +Agent y Settings.
- Para no romper `noUnusedParameters`, **desestructurar solo** `isEditMode` y
  `onToggleEditMode` de las props (las demás quedan en la interfaz sin
  desestructurar; App las sigue pasando → sin unused-locals).
- `SettingsModal` permanece montado en App (invisible; `isSettingsOpen` nunca se
  pone en true). Aceptado como UI muerta de bajo riesgo en esta iteración.

## Lógica nueva, aislada y testeable

Extraer helpers puros (fáciles de probar sin DOM):
- `bandOf(date: Date): 'manana' | 'tarde' | 'noche'` según los cortes 6/12/19.
- `localDayKey(date: Date): string` (YYYY-MM-DD en hora local).
- (Reusar/ajustar `timeLabel` para hora local en vez de slice UTC.)

> Nota: hoy `dayKey`/`timeLabel` cortan el string ISO (UTC). Para franjas en hora
> local hay que usar `new Date(ts)` y sus getters locales. Esto cambia también la
> etiqueta de hora mostrada a hora local (correcto para un dashboard personal).

## Verificación
- `tsc -b && vite build` verde; nuevo bundle servido (hash en index.html).
- Tests unitarios de `bandOf` / `localDayKey` (límites 6:00, 12:00, 19:00, 0:00).
- Visual (usuario, incógnito + DevTools confirmando hash): panel 400px, chips
  togglean, franjas plegables (hoy abierto), ℹ️ arriba-derecha, botón Layout
  abajo-izq entra a modo edición, letra más grande.

## Riesgos
- El +12% de fuente puede apretar algún componente denso (toolbars/modales);
  mitigable ajustando un token puntual.
- Cambiar a hora local altera las etiquetas de hora y el corte de día respecto a
  lo que hoy muestra (UTC). Es el comportamiento deseado.
