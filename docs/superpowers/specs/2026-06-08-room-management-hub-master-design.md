# Diseño MAESTRO — El Room como cabina de gestión

Fecha: 2026-06-08
Rama: room-legibility-3
Tipo: documento MAESTRO. Fija visión, fases y contratos compartidos. Cada fase tiene
su propio spec→plan→deploy. Reemplaza el alcance original "solo legibilidad" del
subsistema E por una visión mayor, **sin romper lo heredado**.

## Visión

El Room deja de ser una bandeja de aprobación y se vuelve la **cabina de gestión** de
todo el sistema de contenido del usuario: redes, video/guiones, guías/mentoring, y un
**RAG para rebotar ideas** sobre sus notas (con opción de **prender el Ryzen** bajo
demanda). Una sola interfaz, varias secciones, sobre el pipeline ya existente
(Perfiles del subsistema A + descubrimiento + drafts).

Secciones objetivo (barra lateral):
- 🏢 **Oficina** — la visualización pixel-art de los agentes trabajando (heredada).
- 📥 **Bandeja (redes)** — aprobar/publicar posts por perfil y cuenta.
- 🎬 **Videos & Guiones** — borradores de guion (largo/short) desde noticias.
- 📚 **Guías & Mentoring** — materiales ligados a libros (*Ser Tutor*, *IA para Docentes*) y cursos.
- 💬 **Preguntar (RAG)** — chat sobre notas/contenido, con botón "⚡ Prender Ryzen".
- 🗓️ **Plan semanal** — rutina tipo "Fama": qué tocaba publicar, qué falta, re-planificar.

> Filosofía guía (Nate Gentile): **"Human First, AI Powered"** — la IA hace lo
> procedimental (descubrir, borrador 0, logística); el humano hace lo creativo.

## Estado actual (verificado en código)

- El Room es un **fork de "Pixel Agents"** (extensión VS Code que visualiza sesiones de
  Claude Code como una oficina). Reusado para el observatorio agregando la pestaña Bandeja.
- **`room/webview-ui/src/App.tsx`**: render monolítico; tab **binario**
  `useState<'office'|'inbox'>`. La Oficina ocupa el panel principal (con `HistoryLog` a
  la derecha); la Bandeja se superpone como `absolute inset-0`.
- **Estado de juego imperativo fuera de React**: `officeStateRef`/`editorState` son
  singletons a nivel de módulo. `OfficeCanvas` queda **montado aunque el tab no sea
  'office'** (solo `display:none`) → el loop sigue corriendo oculto.
- **Transporte** (`transport/index.ts`): singleton con 3 backends (postMessage VS Code,
  SSE, WebSocket). La Oficina consume el **stream de eventos**.
- **`DraftInbox.tsx`**: usa **REST** (`fetch('/api/drafts'...)`), independiente del
  stream. El backend ya devuelve `metadata` completo (incluye `profile_id`/`account`
  tras el subsistema A).
- **Chrome heredado** acoplado en `App.tsx`: `BottomToolbar`, `VersionIndicator`,
  `ChangelogModal`, `SettingsModal` (watchAllSessions/hooks), editor de muebles,
  `MigrationNotice`, tooltips de "Claude Code Hooks".

## Compatibilidad con el canvas heredado (Pixel Agents) — PIEZA CENTRAL

El riesgo no es funcional sino **arquitectónico**: hoy la Oficina *es* la app. Para no
chocar, la Oficina pasa a ser **un módulo más detrás de un shell**. Reglas:

1. **Shell + router**: un componente raíz nuevo (`RoomShell`) con la barra lateral y un
   router simple (estado `section` o hash-routing, sin dependencia pesada). `App.tsx`
   actual se **renombra/encapsula** como el módulo `OfficeSection`, sin tocar su lógica
   interna de canvas/editor.
2. **Montaje perezoso + pausa del loop**: cada sección se monta **solo cuando está
   activa** (lazy + unmount al salir, o al menos pausar). La Oficina **debe pausar su
   RAF/animation loop** cuando no está visible (hoy corre oculta → CPU en la Pi). Esto es
   un requisito explícito, no opcional.
3. **El chrome heredado NO vive en el shell**: `BottomToolbar`, `VersionIndicator`,
   `ChangelogModal`, ajustes de hooks, editor de muebles y `MigrationNotice` quedan
   **dentro de `OfficeSection`** (o se retiran si no aportan al observatorio). El shell
   global solo tiene: barra lateral + el contenedor de la sección activa.
4. **Frontera de datos formalizada**:
   - **Oficina** → stream de eventos (`transport`, SSE/WebSocket).
   - **Secciones de gestión** (Bandeja, Videos, Guías, RAG, Plan) → **REST** (`fetch`
     `/api/...`). Patrón ya usado por `DraftInbox`.
   - Ninguna sección de gestión depende del `OfficeState` ni del game loop.
5. **Sistema de diseño de dos capas**: se comparten **tokens** (colores, spacing, fuente)
   vía CSS variables, pero la Oficina conserva el pixel-art mientras las secciones de
   datos usan **componentes legibles** (no forzar `pixel-panel` en tablas densas — choca
   con la legibilidad pedida). Una capa de componentes UI (`components/ui/`) para datos.
6. **Semántica clara**: la Oficina visualiza a **los agentes del pipeline**
   (Tess/Carla/Edu/Pablo) "trabajando", no sesiones de Claude Code (legado). Ajustar
   copy/labels heredados que aún hablan de "Claude sessions/hooks".
7. **Sin regresiones**: Oficina y Bandeja deben seguir funcionando idénticas tras
   introducir el shell. La migración del tab binario → router es puramente estructural.

## Fases (cada una su propio spec → plan → deploy)

| Fase | Entrega | Depende de |
|------|---------|-----------|
| **E0 — Shell + router** | `RoomShell` con barra lateral; Oficina y Bandeja como secciones; loop de Oficina pausado al salir; chrome heredado encapsulado. **Sin features nuevas.** | — |
| **E1 — Bandeja legible** | Rediseño de tarjeta (legibilidad + etiqueta perfil→cuenta usando `profile_id`/`account`). El E original. | E0 |
| **C — Videos & Guiones** | Formatos `youtube_long`/`youtube_short` en el drafter (research en `docs/research/youtube-scripts`); sección que lista guiones. | E0, A |
| **D — Obsidian hub** | Salida a Obsidian de cada post (archivo + publicar manual fuera de casa); sección de research **ya creada** en el vault. | A |
| **B — Fuentes** | The Batch (Andrew Ng) + re-pesado por perfil. | A |
| **RAG — Preguntar** | Chat sobre notas/contenido (vector store ya existe: ChromaDB) + **Prender Ryzen** (wake-on-LAN del LLM local, con estado dormido/despierto). | E0 |
| **Plan semanal** | Rutina tipo "Fama" sobre Google Calendar + tareas, re-planificación. | E0 |
| **Guías & Mentoring** | Sección ligada a libros/cursos. | E0, C |

**Orden recomendado**: **E0 primero** (desbloquea y aísla lo heredado), luego **E1**
(visible, rápido, dato listo), y en paralelo **C** y **RAG** según energía. B y D pueden
intercalarse. Guías & Mentoring al final.

## Contratos compartidos

- **Navegación**: el shell mantiene `section: 'oficina'|'bandeja'|'videos'|'guias'|'rag'|'plan'`.
  Las secciones no se conocen entre sí; solo el shell sabe cuál está activa.
- **Datos de gestión**: REST sobre `/api/...`; cada sección hace su propio `fetch`.
- **Eventos en vivo**: solo la Oficina (y opcionalmente un indicador global de actividad).
- **Despertar Ryzen**: un endpoint backend `POST /api/ryzen/wake` (wake-on-LAN) + estado
  `GET /api/ryzen/status`; el botón del RAG y cualquier acción que necesite el LLM local
  lo usan. (El observatorio ya sabe si Ollama está vivo vía `check_ollama`.)

## Fuera de alcance de este maestro
- Implementación de cada fase (van en sus specs).
- Despliegue a nano-spud (paso aparte tras cada fase).
- Multiusuario.

## Notas de despliegue
Nada de esto está en nano-spud todavía. El subsistema A está en `main` (PR #26) pero
**sin desplegar**. Cada fase se despliega explícitamente tras merge.
