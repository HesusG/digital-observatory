# Diseño maestro — "Notas → Borradores → Aprobación en el room"

Fecha: 2026-05-30
Rama: room-ui-2
Tipo: documento MAESTRO. Descompone un proyecto grande en 4 fases; cada fase tiene
su propio spec→plan→deploy. Este doc fija alcance, orden y contratos compartidos.

## Visión

Cerrar el lazo de contenido: las **notas de Obsidian** del usuario (carpetas
elegidas) entran como fuente → los agentes (Tess/Carla/Edu) producen **borradores**
(posts sociales y/o blog) → caen en una **bandeja de aprobación dentro del room**
→ el usuario **aprueba/edita/salta/rechaza** → Pablo publica. Hoy el carril de
artículos ya hace casi todo esto vía API; faltan la UI de aprobación, la ingesta de
notas, el selector de carpetas y los formatos de salida extra.

## Estado actual (verificado en código)

- **Aprobación (backend) casi lista**: existen `GET /api/drafts?status=awaiting-user`,
  `POST /api/drafts/{id}/approve` (→ Pablo→Postiz), `/skip`, `/edit`. Falta
  `POST /api/drafts/{id}/reject`. Estados en `drafts_store.py`
  (`DraftStatus`: draft, awaiting-user, scheduled, published, skipped, rejected).
  Un borrador llega a `awaiting-user` cuando Edu da `approved-for-review`.
- **Room (frontend)**: vista única (sin routing). Oficina (canvas) a la izquierda +
  `HistoryLog` (panel absoluto 400px) a la derecha. Las mutaciones se harían con
  `fetch()` (patrón de `HistoryLog`); el SSE transport es solo lectura.
- **Obsidian**: hoy es SALIDA (`outputs/vault.py` escribe drafts al vault). **No**
  hay lector de notas como entrada.
- **Colectores**: `BaseCollector.collect() -> list[CollectedItem]`; `CollectedItem`
  (models.py) tiene `url,title,source,source_type,raw_text,kind,source_group,
  lang_hint,metadata`. `pipeline._collect()` arma e invoca colectores.
- **Vault montado** en el contenedor: `OBSIDIAN_VAULT_PATH=/vault` (docker-compose).

## Decisiones (confirmadas con el usuario)

1. **Tab de aprobación DENTRO del room** ("Oficina | Bandeja").
2. **Selector VISUAL de carpetas** de Obsidian (no solo yaml).
3. **Salidas múltiples**: posts sociales + borradores de blog + combinaciones.
4. **Disparo por botón manual** "Procesar notas".

## Fases (cada una desplegable y verificable sola)

### Fase 1 — Tab de aprobación en el room
**Por qué primero**: la bandeja debe existir antes de llenarla; el backend ya casi
lo soporta → valor inmediato (aprobar los borradores que ya se generan).
- Tab switcher en el room: "Oficina" (lo actual) | "Bandeja".
- Vista Bandeja: lista `awaiting-user` (`GET /api/drafts`), por cada borrador:
  título, plataforma/idioma, contenido, veredicto+razón de Edu. Acciones:
  **Aprobar** (`/approve`), **Editar** (`/edit` con textarea), **Saltar** (`/skip`),
  **Rechazar** (`/reject` — endpoint NUEVO).
- Backend: añadir `POST /api/drafts/{id}/reject` (status→rejected, evento
  `user.rejected`), simétrico a `/skip`.
- Refresco tras cada acción; opcional contador de pendientes en el tab.

### Fase 2 — Notas de Obsidian como fuente + botón "Procesar notas"
- `ObsidianNotesCollector(BaseCollector)`: lee `.md` de las carpetas configuradas,
  extrae título (frontmatter o nombre de archivo) + cuerpo → `CollectedItem(
  kind="article", source="obsidian", source_type="markdown",
  source_group="pedagogy_notes")`.
- Integración en `pipeline._collect()` tras un flag `enable_obsidian`; reusa Tess/
  Carla/Edu → borradores caen en la Bandeja de Fase 1.
- Endpoint `POST /api/collect/obsidian` + botón "Procesar notas" en el room.
- Config inicial de carpetas en `config/sources/obsidian_folders.yaml` (la Fase 3
  lo vuelve editable visualmente).
- Dedup: reusa la dedup por título+texto ya arreglada (PR #20).

### Fase 3 — Selector visual de carpetas
- `GET /api/obsidian/folders`: devuelve el árbol de carpetas del vault (sin leer
  archivos pesados; solo nombres/estructura, profundidad acotada).
- `POST /api/obsidian/folders`: persiste la selección (a `obsidian_folders.yaml` o
  a `state`).
- UI de árbol con checkboxes en el room (en la Bandeja o un panel de ajustes) para
  marcar carpetas/subcarpetas a ingerir; "Procesar notas" usa esa selección.

### Fase 4 — Formatos de salida (blog + combinaciones)
- "Modo blog" para Carla: además de posts, un borrador de artículo largo
  (prompt/format nuevo); nuevo `platform`/tipo "blog" en drafts_store.
- La Bandeja muestra/edita texto largo (blog) distinto de posts cortos.
- Selección por nota/carpeta del formato deseado: solo social / solo blog / ambos
  (campo en la config de carpetas o por colección).

## Contratos compartidos (estables entre fases)

- **Borrador (draft)**: `{id, item_url, platform, lang, content, status,
  edu_verdict, edu_reasoning, postiz_post_id, metadata}`. La Bandeja consume
  `GET /api/drafts`.
- **Acciones**: approve/edit/skip/reject vía `POST /api/drafts/{id}/<action>`.
- **Notas → pipeline**: el colector produce `CollectedItem(kind="article")`; el
  resto del pipeline no cambia (se reutiliza).
- **Eventos**: las acciones de usuario emiten `user.approved|skipped|edited|
  rejected` al event-log (ya existe el patrón).

## Riesgos / notas transversales

- **Trabajo sin desplegar acumulado**: Paco + fixes de pipeline (PR #20 ya merged
  pero el commit de Paco quedó en `room-ui-2` sin llegar a main/Pi). Hay que
  desplegar antes/junto con Fase 1 para no acumular más.
- El room es vista única; el tab switcher es el primer "routing" — mantenerlo
  simple (estado React, no react-router) salvo que crezca.
- Leer el vault: acotar profundidad y tamaño para no colgar el contenedor; el vault
  ya está montado read-only-ish (es el mismo de salida — cuidado con escribir donde
  se lee).
- Postiz solo Bluesky hoy (X/LinkedIn fuera de alcance).

## Plan de ejecución

- **Ahora**: escribir este maestro (hecho) → ejecutar **Fase 1** (spec corto si hace
  falta + plan + implementación + deploy).
- **Después**: Fase 2, luego 3, luego 4 — cada una su propio ciclo, revisada y
  desplegada antes de la siguiente.
- No implementar las 4 fases en una sola tanda (riesgo/contexto).

## Fuera de alcance (de todo el proyecto)
- Postiz X/LinkedIn; agente Moreno fact-checker backend; reescritura del scheduler.
