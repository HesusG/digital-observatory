# Notes → Approval (4 phases) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** In-room approval tab + Obsidian notes as a source (visual folder picker, manual trigger) + blog/social output formats.

**Architecture:** Backend (FastAPI `observatory/`) + room frontend (`room/webview-ui`). Reuses the existing article pipeline and drafts endpoints. Master design: `docs/superpowers/specs/2026-05-30-notes-to-approval-master-design.md`.

**Tech Stack:** Python/FastAPI, ChromaDB, React 19/TS/Vite, `.venv` pytest, `node --test`.

**Proceso:** git SECUENCIAL con `git -C /mnt/data/repos/digital-observatory`; `.venv/bin/python` para pytest; build room con `cd room/webview-ui && npm run build`; deploy al final con autorización.

---

## FASE 1 — Tab de aprobación en el room

### Task 1.1: Endpoint reject (backend)

**Files:** Modify `observatory/app.py`; Test `tests/test_app_drafts.py`

- [ ] **Step 1: Failing test** — en `tests/test_app_drafts.py` añadir (al estilo de los tests existentes de skip):
```python
def test_reject_sets_status_and_logs(client, monkeypatch):
    import observatory.app as app_mod
    calls = {}
    monkeypatch.setattr(app_mod.drafts_store, "mark_rejected",
                        lambda draft_id, reason="user-reject": calls.setdefault("id", draft_id))
    r = client.post("/api/drafts/abc123/reject")
    assert r.status_code == 200
    assert calls["id"] == "abc123"
```
(Si la fixture `client`/estilo difiere, copiar el patrón exacto del test de `/skip` ya presente en ese archivo.)

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_app_drafts.py -q` → FAIL (no `/reject`, no `mark_rejected`).

- [ ] **Step 3: Implement** — en `observatory/storage/drafts_store.py`, junto a `mark_skipped`:
```python
def mark_rejected(draft_id: str, reason: str = "user-reject") -> None:
    _merge_meta(draft_id, {
        "status": DraftStatus.REJECTED.value,
        "reject_reason": reason,
    })
```
En `observatory/app.py`, tras el endpoint `/skip`:
```python
@app.post("/api/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, reason: str = Query(default="user-reject")):
    drafts_store.mark_rejected(draft_id=draft_id, reason=reason)
    event_log.append_event("user", "user.rejected", draft_id=draft_id, payload={"reason": reason})
    return {"status": "ok", "draft_id": draft_id}
```

- [ ] **Step 4: Run** pytest → PASS.

- [ ] **Step 5: Commit** `git -C ... add observatory/app.py observatory/storage/drafts_store.py tests/test_app_drafts.py && git -C ... commit -m "feat(api): POST /api/drafts/{id}/reject"`

### Task 1.2: Tab switcher en App.tsx

**Files:** Modify `room/webview-ui/src/App.tsx`; Create `room/webview-ui/src/components/DraftInbox.tsx`

- [ ] **Step 1: Tab state** — en `App()`, añadir `const [tab, setTab] = useState<'office'|'inbox'>('office');`.

- [ ] **Step 2: Tab bar** — dentro del root `<div className="w-full h-full relative overflow-hidden">`, antes del `containerRef` div, añadir una barra de tabs absoluta arriba-centro (px explícitos por `--spacing:1px`):
```tsx
      <div className="absolute top-0 left-1/2 -translate-x-1/2 z-40 flex gap-2 pixel-panel" style={{ padding: 4 }}>
        <button onClick={() => setTab('office')} className={tab==='office' ? 'text-accent-bright' : ''} style={{ padding: '4px 12px' }}>Oficina</button>
        <button onClick={() => setTab('inbox')} className={tab==='inbox' ? 'text-accent-bright' : ''} style={{ padding: '4px 12px' }}>Bandeja</button>
      </div>
```

- [ ] **Step 3: Conditional render** — envolver el `containerRef` office div con `{tab==='office' && ( ... )}` (todo el bloque de oficina incluido HistoryLog) y añadir `{tab==='inbox' && <DraftInbox />}`. HistoryLog se mantiene solo en la vista office.
  - Nota: el `containerRef`/OfficeCanvas no debe desmontarse al cambiar de tab para no perder el estado del juego → en vez de no-renderizar, ocultar con `style={{ display: tab==='office' ? 'block':'none' }}` en el contenedor office, y renderizar DraftInbox como hermano cuando `tab==='inbox'`.

- [ ] **Step 4: DraftInbox component** — `room/webview-ui/src/components/DraftInbox.tsx`:
```tsx
import { useCallback, useEffect, useState } from 'react';

interface DraftItem { id: string; metadata: Record<string, unknown>; document: string; }

export function DraftInbox() {
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/drafts?status=awaiting-user&limit=100');
      const d = (await r.json()) as { items?: DraftItem[] };
      setDrafts(d.items ?? []);
    } catch { /* offline */ }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function act(id: string, path: string, body?: unknown) {
    setBusy(id);
    try {
      await fetch(`/api/drafts/${id}/${path}`, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      await load();
    } finally { setBusy(null); }
  }

  return (
    <div className="absolute inset-0 overflow-y-auto p-10 flex flex-col gap-6">
      <div className="text-lg text-accent-bright">📥 Bandeja de aprobación ({drafts.length})</div>
      {drafts.length === 0 && <div className="text-sm opacity-50">Sin borradores pendientes.</div>}
      {drafts.map((d) => {
        const m = d.metadata as { platform?: string; lang?: string; item_title?: string; edu_reasoning?: string };
        return (
          <div key={d.id} className="pixel-panel p-8 flex flex-col gap-4">
            <div className="text-sm text-accent-bright">{m.item_title || '(sin título)'} · {m.platform}/{m.lang}</div>
            <div className="text-sm whitespace-pre-wrap">{d.document}</div>
            {m.edu_reasoning && <div className="text-2xs opacity-60">Edu: {m.edu_reasoning}</div>}
            <div className="flex gap-3">
              <button disabled={busy===d.id} onClick={() => act(d.id,'approve')} className="pixel-panel px-6 py-2 text-accent-bright">Aprobar</button>
              <button disabled={busy===d.id} onClick={() => { const c = prompt('Editar contenido:', d.document); if (c) void act(d.id,'edit',{content:c}); }} className="pixel-panel px-6 py-2">Editar</button>
              <button disabled={busy===d.id} onClick={() => act(d.id,'skip')} className="pixel-panel px-6 py-2 opacity-70">Saltar</button>
              <button disabled={busy===d.id} onClick={() => act(d.id,'reject')} className="pixel-panel px-6 py-2 opacity-70">Rechazar</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Build** `cd room/webview-ui && npm run build` → verde (TS estricto). Import de `DraftInbox` en App.tsx.

- [ ] **Step 6: Commit** source (sin dist todavía; dist al final de cada fase o al deploy).
`git -C ... add room/webview-ui/src/App.tsx room/webview-ui/src/components/DraftInbox.tsx && git -C ... commit -m "feat(room): approval inbox tab (office | bandeja)"`

---

## FASE 2 — Notas de Obsidian como fuente + botón "Procesar notas"

### Task 2.1: ObsidianNotesCollector

**Files:** Create `observatory/collectors/obsidian.py`; Create `config/sources/obsidian_folders.yaml`; Test `tests/test_obsidian_collector.py`

- [ ] **Step 1: Failing test** — crear `tests/test_obsidian_collector.py` que apunte el colector a un tmp dir con 2 `.md` (uno con frontmatter `title:`, otro sin) y verifique que produce 2 `CollectedItem` con `kind=="article"`, `source_type=="markdown"`, título correcto (frontmatter o nombre de archivo), `raw_text` = cuerpo.

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_obsidian_collector.py -q` → FAIL.

- [ ] **Step 3: Implement** `observatory/collectors/obsidian.py` — `class ObsidianNotesCollector(BaseCollector)` con `name="obsidian"`, `source_type="markdown"`; `__init__(self, vault_path=None, folders=None)` (lee defaults de `settings.obsidian_vault_path` y de `config/sources/obsidian_folders.yaml`); `async def collect()` recorre cada carpeta seleccionada (recursivo opcional), lee `*.md` (acotar tamaño/profundidad), parsea frontmatter YAML simple (título), construye `CollectedItem(url=f"obsidian://{relpath}", title=..., source=folder_name, source_type="markdown", raw_text=body, kind="article", source_group="pedagogy_notes", lang_hint=...)`. Devuelve la lista.
  - `config/sources/obsidian_folders.yaml` inicial:
    ```yaml
    enabled: true
    folders:
      - path: "Pedagogía"
        recursive: true
    ```

- [ ] **Step 4: Run** pytest → PASS.

- [ ] **Step 5: Commit** `feat(collectors): ObsidianNotesCollector reads vault notes as articles`

### Task 2.2: Integración en pipeline + endpoint + botón

**Files:** Modify `observatory/pipeline.py` (`_collect` + `run_pipeline` flag `enable_obsidian`); Modify `observatory/app.py` (POST `/api/collect/obsidian`); Modify `room/webview-ui/src/components/DraftInbox.tsx` (botón "Procesar notas")

- [ ] **Step 1** — en `pipeline._collect()` añadir `enable_obsidian: bool=False`; si true, instanciar `ObsidianNotesCollector()` y `tasks.append(it.collect())`. En `run_pipeline` propagar el flag. (Reusa dedup título+texto ya arreglada.)
- [ ] **Step 2** — endpoint:
```python
@app.post("/api/collect/obsidian")
async def collect_obsidian():
    res = await run_pipeline(enable_rss=False, enable_wordpress=False, enable_obsidian=True)
    return {"status": "ok", "new_items": res.new_items, "drafted": res.articles_drafted}
```
- [ ] **Step 3** — en DraftInbox, botón "Procesar notas" que hace `POST /api/collect/obsidian` y luego `load()`.
- [ ] **Step 4** — build + `python -c "import observatory.pipeline, observatory.app"`; tests verdes.
- [ ] **Step 5** — Commit `feat(pipeline): obsidian notes source + /api/collect/obsidian + button`

---

## FASE 3 — Selector visual de carpetas

**Files:** Modify `observatory/app.py` (GET/POST `/api/obsidian/folders`); Modify `observatory/collectors/obsidian.py` (leer selección persistida); Modify `room/webview-ui/src/components/DraftInbox.tsx` o nuevo `FolderPicker.tsx`

- [ ] **Step 1** — `GET /api/obsidian/folders`: helper en `obsidian.py` `list_vault_folders(max_depth=3) -> list[str]` (solo nombres de carpetas, sin leer archivos), endpoint lo devuelve. Test del helper sobre tmp dir.
- [ ] **Step 2** — `POST /api/obsidian/folders` body `{folders: [...]}` → persiste a `obsidian_folders.yaml` (o a `state`). El colector lee esa selección.
- [ ] **Step 3** — UI `FolderPicker`: fetch del árbol, checkboxes, guardar selección (POST). Montado en la Bandeja (sección "Carpetas").
- [ ] **Step 4** — build + tests; Commit `feat: visual obsidian folder picker`

---

## FASE 4 — Formatos de salida (blog + combinaciones)

**Files:** Modify `observatory/intelligence/drafter.py` (modo blog); Modify `observatory/storage/drafts_store.py` (platform "blog"); Modify `observatory/pipeline.py` (generar blog además de social); Modify `DraftInbox.tsx` (mostrar/editar texto largo)

- [ ] **Step 1** — `drafter.py`: función/param para generar un borrador de **blog** (prompt nuevo, sin límite de caracteres de social), devolviendo `platform="blog"`.
- [ ] **Step 2** — en `carla_draft_for_item`, además de social, generar un draft `platform="blog"` cuando la nota/carpeta lo pida (campo `formats: [social, blog]` en `obsidian_folders.yaml`; default social).
- [ ] **Step 3** — DraftInbox: si `platform==='blog'`, render con textarea más grande y vista de texto largo; editar usa `<textarea>` en vez de `prompt()`.
- [ ] **Step 4** — tests del prompt builder (que el modo blog produzca prompt distinto/sin límite); build; Commit `feat: blog draft format + long-text inbox editing`

---

## Deploy final (tras las 4 fases)

- [ ] Build room: `cd room/webview-ui && npm run build` → anotar hash.
- [ ] Stage dist en trozos (index.html + nuevo js/css + borrados); verificar `git ls-tree`.
- [ ] Tests backend completos: `.venv/bin/python -m pytest tests/ -q` → all pass.
- [ ] Commit dist; push; PR; merge (usuario); deploy Pi (`git pull && docker compose up -d --build observatory`) con autorización.
- [ ] Verificar EN VIVO: tab Bandeja lista borradores; "Procesar notas" genera borradores desde el vault; selector de carpetas; blog drafts. (Requiere que el vault tenga notas en las carpetas elegidas.)

## Notas
- TDD en helpers backend (reject store, obsidian collector, folder lister, blog prompt). UI por build + verificación en vivo.
- Vault montado read en `/vault`; NO escribir en carpetas que se leen.
- Git secuencial; `.git/index.lock` → borrar y reintentar.
- Desplegar también arrastra Paco + fixes de pipeline pendientes.
