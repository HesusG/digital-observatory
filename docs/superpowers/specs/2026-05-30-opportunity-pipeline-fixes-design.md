# Diseño — Arreglo del pipeline de oportunidades (Telegram, dedup, eventos, stats)

Fecha: 2026-05-30
Rama: room-ui-2 (backend del observatory; NO el room/webview-ui)
Alcance: backend Python (`observatory/`, `config/`). Sin cambios de frontend.

## Contexto y diagnóstico (causa raíz, con evidencia en vivo del Pi)

El usuario reporta: no llegan notificaciones de Telegram seguido; no ve "logs de
oportunidades de RSS"; cree que está en esqueleto.

Investigación (systematic-debugging) sobre producción (`100.84.156.15:8400`):
- El pipeline **SÍ corre** (`/api/pipeline/status` → `last_run` de hoy). No es
  falta de scheduler.
- `POST /api/pipeline/run` → `collected: 359, duplicates: 359, new_items: 0,
  evaluated: 0`. **El 100% de lo recolectado se marca duplicado.**
- Log real: `Semantic duplicate (distance=0.001): '…fundsforngos.org/individuals/
  submissions-open…' ≈ '…fundsforngos.org/arts-culture-2/submit-applicat…'` →
  dos oportunidades DISTINTAS coladas como duplicadas a distancia 0.001.
- ChromaDB tiene 634 oportunidades; 298 con summary (evaluadas); **18 con
  affinity ≥ 8** (umbral Telegram). 336 con score 0 (nunca evaluadas).
- `/api/stats` hace **timeout** (recorre toda la colección + tormenta de llamadas
  redundantes a ChromaDB).

### Las 5 causas
1. **Telegram solo se envía en el momento de evaluar un item `new`** (pipeline.py
   :126-140). Como `new_items: 0`, no se reevalúa ni se reintenta; los 18 ≥8 que
   calificaron solo tuvieron un disparo único (perdido si falló). No hay cola ni
   resumen.
2. **Dedup semántico con falsos positivos masivos**: se embebe `raw_text[:2000]`
   (chromadb_store.upsert_item:91) — boilerplate casi idéntico entre fuentes →
   distancia ~0.001; umbral `dedup_distance_threshold=0.15` (settings.py:44) las
   mata. Bloquea oportunidades nuevas incluso en su primer ingest.
3. **La rama de oportunidades NO emite eventos** al event-log (pipeline.py:98-140
   no llama `event_log.append_event`), a diferencia de la de artículos
   (pipeline.py:180-198). Por eso no se ven en el cuarto ni en `/api/events`.
4. **Ineficiencia**: `/api/stats` (app.py:400) y el camino caliente del dedup
   hacen demasiadas llamadas a ChromaDB → timeout.
5. (Confirmado, no-bug) El scheduler externo existe y dispara el pipeline.

## Fixes (aprobados por el usuario: las 4 + resumen diario top-N)

### Fix #2 — Dedup (causa raíz; desbloquea el flujo)
- **Embeber texto distintivo**: en `upsert_item` y en el camino de dedup, usar
  `f"{title}. {raw_text}"` (el título diferencia oportunidades) en vez de solo
  `raw_text[:2000]`. Mantener `clean_for_embedding`.
- **Recalibrar el umbral** con un spike sobre datos reales del Pi (comparar
  distancias de pares conocidos-distintos vs conocidos-iguales). Punto de partida:
  bajar `dedup_distance_threshold` (0.15 → ~0.05) — VALOR FINAL lo fija el spike,
  documentado en el plan.
- **Intacto**: dedup por URL exacta (`url_exists`) no se toca.

### Fix #1 — Resumen diario top-N por Telegram
- Nueva función `send_daily_opportunity_digest()` (en `outputs/telegram.py` o un
  `outputs/digest.py`): lee de ChromaDB las oportunidades con `collected_at` del
  día y `affinity_score >= high_affinity_threshold`, ordena desc, toma top-N
  (config `daily_digest_top_n`, default 5), arma un mensaje y lo envía.
- **Idempotente por día**: marca en `state` (`daily_digest_sent` con fecha), igual
  que el weekly email (`PipelineState`). Disparada al final de `run_pipeline`.
- Se mantiene el alert inmediato existente (no se rompe).

### Fix #3 — Eventos de oportunidades
- En la rama de oportunidades de `run_pipeline` (después de evaluar), emitir:
  - `tess.scored` con `payload={title, affinity_score, category}`.
  - si `affinity_score < min` (nuevo `opportunity_min_affinity`, default 0 = loguear
    todas) o evaluación nula → `tess.skipped` con razón.
  - Reusar `event_log.append_event` con `run_id`. (Mismo patrón que artículos.)
- Resultado: oportunidades visibles en el cuarto y en `/api/events`.

### Fix #4 — Eficiencia / stats
- `/api/stats`: usar `collection.count()` (ChromaDB nativo) en vez de traer todos
  los metadatos; si necesita desglose por kind, acotar.
- Dedup: asegurar **una** query por item (revisar que `find_nearest` no dispare
  llamadas repetidas); no recalcular el embedding fn por item.

## Lógica testeable
- Helper puro de selección del digest: `pick_top_opportunities(items, n, min_score)`
  → ordena por score desc y filtra ≥min, top-N. Test con `pytest`/unittest.
- `clean_for_embedding` ya existe; añadir test de que título+texto produce input no
  vacío y distinto para títulos distintos (sanity).

## Verificación (en vivo, no a ciegas)
- Spike: medir distribución de distancias en datos reales → fijar umbral.
- Tras desplegar: `POST /api/pipeline/run` y confirmar `new_items > 0`,
  `evaluated > 0`, aparición de eventos `tess.*` de oportunidades en `/api/events`,
  y recepción del digest diario en Telegram. `/api/stats` responde sin timeout.

## Riesgos
- Bajar el umbral de dedup de más → entran duplicados reales. Mitigado por el
  spike de calibración y por mantener dedup-por-URL.
- Cambiar el texto embebido **invalida** las distancias de items ya almacenados
  (vectores viejos vs nuevos). Aceptable: los nuevos se comparan entre sí; no se
  re-embebe el histórico en esta iteración (follow-up opcional).
- El digest podría duplicar el alert inmediato; aceptable (resumen vs puntual).

## Fuera de alcance
- Re-embeber/re-evaluar el histórico de 634 items.
- Postiz X/LinkedIn; agentes; cambios de scheduler.
