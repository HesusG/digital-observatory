# Opportunity Pipeline Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Desbloquear el pipeline de oportunidades: arreglar el dedup de falsos positivos, emitir eventos de oportunidades al event-log, añadir un resumen diario de Telegram, y quitar el timeout de /api/stats.

**Architecture:** Backend Python (`observatory/`). El cambio raíz es embeber `título + texto` y recalibrar el umbral de dedup (calibrado con un spike sobre datos reales). Encima: eventos `tess.*` para oportunidades, un digest diario idempotente (patrón del weekly email), y un /api/stats que no carga el modelo de embeddings.

**Tech Stack:** Python, FastAPI, ChromaDB (SentenceTransformer all-MiniLM-L6-v2), SQLite state, httpx (Telegram), pytest/unittest.

**Proceso:** git SECUENCIAL con `git -C /mnt/data/repos/digital-observatory`. Verificación EN VIVO en el Pi tras desplegar (no a ciegas). El backend corre en el contenedor `observatory`; el deploy es `git pull && docker compose up -d --build observatory` en nano-spud (requiere autorización del usuario).

---

### Task 1: Calibrar el umbral de dedup (spike con datos reales)

**Files:** ninguno (investigación). Produce el número para Task 2.

- [ ] **Step 1: Run the calibration spike on the Pi**

Ya hay un script en `/tmp/spike.py` (copiado al contenedor) que mide distancias
coseno entre oportunidades DISTINTAS usando (a) `raw_text` y (b) `título+texto`.
Correr en el contenedor:
```bash
ssh nano-spud 'docker exec observatory python /tmp/spike.py'
```
Si no existe, recrearlo: descargar `/api/items/recent?kind=opportunity` a opps.json,
embeber con `SentenceTransformerEmbeddingFunction('all-MiniLM-L6-v2')`, normalizar,
y reportar percentiles de distancia + cuántos pares caerían bajo 0.05 y 0.15.

- [ ] **Step 2: Decide the threshold**

De la salida, elegir `dedup_distance_threshold` tal que:
- pares de oportunidades DISTINTAS queden por ENCIMA (no se fusionen), y
- siga atrapando re-scrapes casi idénticos.
Regla: usar ~el percentil 1 de las distancias `título+texto` redondeado hacia
abajo, acotado a [0.02, 0.08]. **Anotar el valor elegido aquí:** `THRESHOLD=____`.

> Si el spike muestra que con `título+texto` los distintos ya quedan >0.10, basta
> con cambiar el texto embebido y dejar 0.08 como umbral conservador.

---

### Task 2: Fix dedup — embeber título+texto + umbral calibrado

**Files:**
- Modify: `observatory/storage/chromadb_store.py` (`upsert_item` documento embebido)
- Modify: `observatory/processing/deduplicator.py` (texto de consulta)
- Modify: `config/settings.py` (`dedup_distance_threshold`)
- Test: `tests/test_dedup_text.py` (nuevo)

- [ ] **Step 1: Write a failing test for the embedded-text builder**

Crear un helper puro para construir el texto a embeber y testearlo.
`tests/test_dedup_text.py`:
```python
from observatory.processing.embedder import build_embedding_text

def test_distinct_titles_produce_distinct_text():
    a = build_embedding_text("Waislitz Award 2026", "Apply now for funding.")
    b = build_embedding_text("Mandela Rhodes Prize", "Apply now for funding.")
    assert a != b
    assert a.startswith("Waislitz Award 2026")

def test_empty_title_falls_back_to_text():
    assert build_embedding_text("", "Some body text") == "Some body text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/repos/digital-observatory && python -m pytest tests/test_dedup_text.py -q`
Expected: FAIL — `build_embedding_text` no existe.

- [ ] **Step 3: Implement build_embedding_text**

En `observatory/processing/embedder.py`, añadir:
```python
def build_embedding_text(title: str, raw_text: str, max_chars: int = 2000) -> str:
    """Text used for semantic dedup/embedding. Prefix the title so that items
    sharing boilerplate body text (common across opportunity sites) still embed
    distinctly. Falls back to raw_text when title is empty."""
    title = (title or "").strip()
    body = clean_for_embedding(raw_text or "", max_chars=max_chars)
    if not title:
        return body
    return clean_for_embedding(f"{title}. {raw_text or ''}", max_chars=max_chars)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dedup_text.py -q`
Expected: PASS.

- [ ] **Step 5: Use it in upsert + dedup**

En `observatory/storage/chromadb_store.py`, en `upsert_item`, reemplazar:
```python
    # Truncate raw_text for embedding (MiniLM handles ~256 word pieces)
    truncated = raw_text[:2000]

    collection.upsert(ids=[doc_id], documents=[truncated], metadatas=[metadata])
```
por:
```python
    from observatory.processing.embedder import build_embedding_text
    document = build_embedding_text(title, raw_text)

    collection.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])
```

En `observatory/processing/deduplicator.py`, `is_duplicate(raw_text, url)` no tiene
el título. Cambiar su firma a `is_duplicate(raw_text, url, title="")` y usar
`build_embedding_text(title, raw_text)` en vez de `clean_for_embedding(raw_text)`:
```python
from observatory.processing.embedder import build_embedding_text
...
def is_duplicate(raw_text: str, url: str, title: str = "") -> tuple[bool, str | None]:
    if chromadb_store.url_exists(url):
        return True, url
    cleaned = build_embedding_text(title, raw_text)
    distance, metadata = chromadb_store.find_nearest(cleaned)
    ...
```
Y en `observatory/pipeline.py` (línea ~75), pasar el título:
```python
        dup, dup_of = is_duplicate(item.raw_text, item.url, item.title)
```

- [ ] **Step 6: Set the calibrated threshold**

En `config/settings.py`, cambiar:
```python
    dedup_distance_threshold: float = 0.15
```
por el valor de Task 1 (anotado como THRESHOLD), p.ej.:
```python
    dedup_distance_threshold: float = 0.08
```

- [ ] **Step 7: Verify build/tests**

Run: `python -m pytest tests/test_dedup_text.py -q`
Expected: PASS. (No romper imports: `python -c "import observatory.pipeline"`.)

- [ ] **Step 8: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add observatory/processing/embedder.py observatory/storage/chromadb_store.py observatory/processing/deduplicator.py observatory/pipeline.py config/settings.py tests/test_dedup_text.py
git -C /mnt/data/repos/digital-observatory commit -m "fix(pipeline): embed title+text for dedup + calibrated threshold"
```

---

### Task 3: Emitir eventos de oportunidades al event-log

**Files:**
- Modify: `observatory/pipeline.py` (rama de oportunidades, líneas ~98-140)

- [ ] **Step 1: Append events in the opportunity branch**

En `observatory/pipeline.py`, en la rama de oportunidades, tras obtener
`evaluation` (después de `update_item_evaluation`), añadir el evento scored, y
manejar el caso nulo como skipped. Reemplazar el bloque actual:
```python
        evaluation = await evaluate_opportunity(item.raw_text)

        if evaluation is None:
            result.eval_failures += 1
            metrics.llm_errors.labels(provider="unknown").inc()
            continue

        result.evaluated += 1
        metrics.items_evaluated.labels(source=item.source).inc()

        chromadb_store.update_item_evaluation(
            url=item.url,
            affinity_score=evaluation.affinity_score,
            category=evaluation.category,
            summary=evaluation.summary,
            reasoning=evaluation.reasoning,
            is_free_or_funded=evaluation.is_free_or_funded,
        )
```
por:
```python
        evaluation = await evaluate_opportunity(item.raw_text)

        if evaluation is None:
            result.eval_failures += 1
            metrics.llm_errors.labels(provider="unknown").inc()
            event_log.append_event(
                "tess", "tess.skipped",
                item_url=item.url, run_id=run_id,
                payload={"title": item.title, "skip_reason": "eval-failed"},
            )
            continue

        result.evaluated += 1
        metrics.items_evaluated.labels(source=item.source).inc()

        chromadb_store.update_item_evaluation(
            url=item.url,
            affinity_score=evaluation.affinity_score,
            category=evaluation.category,
            summary=evaluation.summary,
            reasoning=evaluation.reasoning,
            is_free_or_funded=evaluation.is_free_or_funded,
        )

        event_log.append_event(
            "tess", "tess.scored",
            item_url=item.url, run_id=run_id,
            payload={
                "title": item.title,
                "affinity_score": evaluation.affinity_score,
                "category": evaluation.category,
            },
        )
```
(`run_id` ya está en scope dentro de `run_pipeline`. `event_log` ya está importado.)

- [ ] **Step 2: Verify import**

Run: `cd /mnt/data/repos/digital-observatory && python -c "import observatory.pipeline"`
Expected: sin error.

- [ ] **Step 3: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add observatory/pipeline.py
git -C /mnt/data/repos/digital-observatory commit -m "feat(pipeline): emit tess.scored/skipped events for opportunities"
```

---

### Task 4: Resumen diario de Telegram (top-N idempotente)

**Files:**
- Create: `observatory/outputs/digest.py`
- Modify: `observatory/storage/state.py` (idempotencia diaria)
- Modify: `config/settings.py` (`daily_digest_top_n`)
- Modify: `observatory/pipeline.py` (invocar al final)
- Test: `tests/test_digest_pick.py` (nuevo)

- [ ] **Step 1: Write a failing test for the top-N picker**

`tests/test_digest_pick.py`:
```python
from observatory.outputs.digest import pick_top_opportunities

def test_filters_below_threshold_and_sorts_desc():
    items = [
        {"title": "a", "score": 9},
        {"title": "b", "score": 4},
        {"title": "c", "score": 8},
        {"title": "d", "score": 10},
    ]
    out = pick_top_opportunities(items, n=2, min_score=8)
    assert [i["title"] for i in out] == ["d", "a"]

def test_respects_n():
    items = [{"title": str(i), "score": 9} for i in range(5)]
    assert len(pick_top_opportunities(items, n=3, min_score=8)) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_digest_pick.py -q`
Expected: FAIL — módulo `digest` no existe.

- [ ] **Step 3: Implement digest.py**

`observatory/outputs/digest.py`:
```python
import logging
from datetime import datetime

from config.settings import settings
from observatory.storage import chromadb_store
from observatory.outputs.telegram import _send_message  # see Task 4 step 5

logger = logging.getLogger(__name__)


def pick_top_opportunities(items: list[dict], n: int, min_score: int) -> list[dict]:
    """Pure: filter items with score >= min_score, sort by score desc, take n."""
    eligible = [i for i in items if int(i.get("score", 0) or 0) >= min_score]
    eligible.sort(key=lambda i: int(i.get("score", 0) or 0), reverse=True)
    return eligible[:n]


def _format_digest(items: list[dict]) -> str:
    lines = [f"📬 *Oportunidades del día* ({len(items)})", ""]
    for i in items:
        lines.append(f"⭐ *{i['score']}/10* — {i['title']}")
        if i.get("url"):
            lines.append(i["url"])
        lines.append("")
    return "\n".join(lines).strip()


async def send_daily_opportunity_digest(items: list[dict]) -> bool:
    """items: [{title, url, score}]. Sends a single Telegram message. Returns
    True if sent (or nothing to send -> False)."""
    top = pick_top_opportunities(items, settings.daily_digest_top_n, settings.high_affinity_threshold)
    if not top:
        return False
    return await _send_message(_format_digest(top))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_digest_pick.py -q`
Expected: PASS.

- [ ] **Step 5: Extract a reusable Telegram sender**

En `observatory/outputs/telegram.py`, factorizar el POST en una función reutilizable
`_send_message(text: str) -> bool` (lee token/chat_id de settings, hace el POST a
`sendMessage` con `parse_mode: Markdown`, devuelve bool). Hacer que
`send_telegram_alert` la use. (Reusa el código de POST que ya existe; no dupликar.)

- [ ] **Step 6: Add settings + state idempotency**

`config/settings.py`: añadir
```python
    daily_digest_top_n: int = 5
```
`observatory/storage/state.py`: añadir
```python
    def should_send_daily_digest(self) -> bool:
        last = self.get("last_daily_digest")
        if not last:
            return True
        return datetime.fromisoformat(last).date() < datetime.now().date()

    def mark_daily_digest_sent(self):
        self.set("last_daily_digest", datetime.now().isoformat())
```

- [ ] **Step 7: Invoke at the end of run_pipeline**

En `observatory/pipeline.py`, añadir un helper y llamarlo antes del return de
`run_pipeline` (junto a `_maybe_send_weekly_email`):
```python
async def _maybe_send_daily_digest(run_id: str) -> None:
    from datetime import datetime, timedelta
    from observatory.outputs.digest import send_daily_opportunity_digest
    state = PipelineState(settings.state_db_path)
    if not state.should_send_daily_digest():
        return
    since = datetime.utcnow() - timedelta(hours=24)
    try:
        recent = chromadb_store.get_recent_items(since=since, kind="opportunity")
    except Exception as exc:
        logger.warning(f"daily digest: recent fetch failed: {exc}")
        return
    items = [
        {
            "title": r.get("metadata", {}).get("title", ""),
            "url": r.get("metadata", {}).get("url", ""),
            "score": int(r.get("metadata", {}).get("affinity_score", 0) or 0),
        }
        for r in recent
    ]
    sent = await send_daily_opportunity_digest(items)
    if sent:
        state.mark_daily_digest_sent()
        metrics.notifications_sent.labels(channel="telegram").inc()
```
Y en `run_pipeline`, antes de `await _maybe_send_weekly_email()`:
```python
    await _maybe_send_daily_digest(run_id)
```

- [ ] **Step 8: Verify build/tests**

Run: `python -m pytest tests/test_digest_pick.py tests/test_dedup_text.py -q && python -c "import observatory.pipeline, observatory.outputs.digest"`
Expected: PASS, sin errores de import.

- [ ] **Step 9: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add observatory/outputs/digest.py observatory/outputs/telegram.py observatory/storage/state.py config/settings.py observatory/pipeline.py tests/test_digest_pick.py
git -C /mnt/data/repos/digital-observatory commit -m "feat(outputs): daily Telegram opportunity digest (top-N, idempotent)"
```

---

### Task 5: /api/stats sin timeout

**Files:**
- Modify: `observatory/app.py` (`/api/stats`)

- [ ] **Step 1: Make stats cheap (no model load)**

El timeout viene de que `get_items_collection()` instancia el embedding model en la
primera llamada. `collection.count()` no necesita embeddings. Crear/asegurar un
acceso a la colección SIN `embedding_function` para conteo, o envolver el count en
un timeout corto. Cambiar `/api/stats` para que devuelva rápido:
```python
@app.get("/api/stats")
async def stats():
    try:
        total = chromadb_store.get_item_count()
    except Exception as exc:
        total = None
        logger.warning(f"stats count failed: {exc}")
    return {
        "total_items": total,
        "chromadb_host": f"{settings.chroma_host}:{settings.chroma_port}",
    }
```
Y en `chromadb_store.py`, añadir `get_item_count_fast()` que use un cliente/colección
sin embedding_function:
```python
def get_item_count_fast() -> int:
    client = _get_client()
    col = client.get_or_create_collection(name="items")  # no embedding_fn needed for count
    return col.count()
```
y que `/api/stats` use `get_item_count_fast()`.

> Nota: si `get_or_create_collection` sin embedding_fn choca con la colección ya
> creada con una, usar `client.get_collection(name="items")` (sin embedding_fn) para
> el count.

- [ ] **Step 2: Verify import**

Run: `python -c "import observatory.app"`
Expected: sin error.

- [ ] **Step 3: Commit**

```bash
git -C /mnt/data/repos/digital-observatory add observatory/app.py observatory/storage/chromadb_store.py
git -C /mnt/data/repos/digital-observatory commit -m "fix(api): /api/stats counts without loading the embedding model"
```

---

### Task 6: Deploy + verificación en vivo

- [ ] **Step 1: Push**

```bash
git -C /mnt/data/repos/digital-observatory push origin room-ui-2
```

- [ ] **Step 2: PR + merge (usuario)**

```bash
gh pr create --base main --head room-ui-2 \
  --title "fix(observatory): desbloquear pipeline de oportunidades (dedup, eventos, digest, stats)" \
  --body "Embed título+texto + umbral calibrado (dedup falsos positivos); eventos tess.* para oportunidades; resumen diario de Telegram top-N idempotente; /api/stats sin timeout."
```

- [ ] **Step 3: Deploy (con autorización)**

```bash
ssh nano-spud 'cd /home/d3r/repos/digital-observatory && git pull --ff-only origin main && docker compose up -d --build observatory'
```

- [ ] **Step 4: Verify LIVE (datos reales)**

```bash
# /api/stats responde rápido
time curl -sS --max-time 10 http://100.84.156.15:8400/api/stats
# pipeline ahora produce items nuevos + evaluados
curl -sS -X POST --max-time 200 http://100.84.156.15:8400/api/pipeline/run
#   → esperar new_items > 0, evaluated > 0
# eventos de oportunidades aparecen
curl -sS "http://100.84.156.15:8400/api/events?limit=50" | python3 -c "import sys,json;from collections import Counter;e=json.load(sys.stdin)['events'];print(Counter(x['event_type'] for x in e))"
# Telegram: confirmar que llegó el digest diario al chat del usuario
```
Expected: `new_items > 0`, `evaluated > 0`, eventos `tess.scored` de oportunidades,
y un mensaje de digest en Telegram. El usuario confirma la recepción en su teléfono.

---

## Notas de ejecución
- TDD en Tasks 2 y 4 (helpers puros). Resto: verificación por import + en vivo.
- El cambio de texto embebido invalida distancias de items viejos vs nuevos; los
  nuevos se comparan entre sí (aceptable; re-embeber histórico = follow-up).
- Git SECUENCIAL; borrar `.git/index.lock` si segfalla.
- El deploy de producción requiere autorización explícita del usuario.
