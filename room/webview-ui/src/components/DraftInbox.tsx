import { useCallback, useEffect, useState } from 'react';

interface DraftItem {
  id: string;
  metadata: Record<string, unknown>;
  document: string;
}

// Approval inbox: lists drafts in status "awaiting-user" and lets the user
// approve / edit / skip / reject them via the /api/drafts endpoints.
export function DraftInbox() {
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showFolders, setShowFolders] = useState(false);
  const [available, setAvailable] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  const loadFolders = useCallback(async () => {
    try {
      const r = await fetch('/api/obsidian/folders');
      const d = (await r.json()) as { available?: string[]; selected?: string[] };
      setAvailable(d.available ?? []);
      setSelected(d.selected ?? []);
    } catch {
      /* offline */
    }
  }, []);

  async function toggleFolder(path: string) {
    const next = selected.includes(path)
      ? selected.filter((p) => p !== path)
      : [...selected, path];
    setSelected(next);
    try {
      await fetch('/api/obsidian/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folders: next }),
      });
    } catch {
      /* offline */
    }
  }

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/drafts?status=awaiting-user&limit=100');
      const d = (await r.json()) as { items?: DraftItem[] };
      setDrafts(d.items ?? []);
    } catch {
      /* offline */
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(id: string, path: string, body?: unknown) {
    setBusy(id);
    try {
      await fetch(`/api/drafts/${id}/${path}`, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function processNotes() {
    setProcessing(true);
    try {
      await fetch('/api/collect/obsidian', { method: 'POST' });
      await load();
    } catch {
      /* offline */
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="absolute inset-0 overflow-y-auto p-10 flex flex-col gap-6">
      <div className="flex items-center gap-6">
        <div className="text-lg text-accent-bright">📥 Bandeja de aprobación ({drafts.length})</div>
        <button
          onClick={processNotes}
          disabled={processing}
          className="pixel-panel px-6 py-2 text-sm"
          title="Procesar notas de Obsidian"
        >
          {processing ? 'Procesando…' : '📝 Procesar notas'}
        </button>
        <button onClick={() => void load()} className="pixel-panel px-6 py-2 text-sm" title="Refrescar">
          ↻
        </button>
        <button
          onClick={() => {
            const next = !showFolders;
            setShowFolders(next);
            if (next) void loadFolders();
          }}
          className="pixel-panel px-6 py-2 text-sm"
          title="Elegir carpetas de Obsidian"
        >
          📁 Carpetas
        </button>
      </div>

      {showFolders && (
        <div className="pixel-panel p-8 flex flex-col gap-2">
          <div className="text-sm text-accent-bright">Carpetas a procesar</div>
          {available.length === 0 && (
            <div className="text-2xs opacity-50">No se encontraron carpetas en el vault.</div>
          )}
          {available.map((f) => (
            <label key={f} className="text-sm flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(f)}
                onChange={() => void toggleFolder(f)}
              />
              {f}
            </label>
          ))}
        </div>
      )}

      {drafts.length === 0 && (
        <div className="text-sm opacity-50">Sin borradores pendientes.</div>
      )}

      {drafts.map((d) => {
        const m = d.metadata as {
          platform?: string;
          lang?: string;
          item_title?: string;
          edu_reasoning?: string;
        };
        const isBlog = m.platform === 'blog';
        return (
          <div key={d.id} className="pixel-panel p-8 flex flex-col gap-4">
            <div className="text-sm text-accent-bright">
              {m.item_title || '(sin título)'} · {m.platform}/{m.lang}
            </div>
            <div
              className="text-sm whitespace-pre-wrap"
              style={isBlog ? { maxHeight: 240, overflowY: 'auto' } : undefined}
            >
              {d.document}
            </div>
            {m.edu_reasoning && (
              <div className="text-2xs opacity-60">Edu: {m.edu_reasoning}</div>
            )}
            <div className="flex flex-wrap gap-3">
              <button
                disabled={busy === d.id}
                onClick={() => void act(d.id, 'approve')}
                className="pixel-panel px-6 py-2 text-accent-bright"
              >
                Aprobar
              </button>
              <button
                disabled={busy === d.id}
                onClick={() => {
                  const c = prompt('Editar contenido:', d.document);
                  if (c) void act(d.id, 'edit', { content: c });
                }}
                className="pixel-panel px-6 py-2"
              >
                Editar
              </button>
              <button
                disabled={busy === d.id}
                onClick={() => void act(d.id, 'skip')}
                className="pixel-panel px-6 py-2 opacity-70"
              >
                Saltar
              </button>
              <button
                disabled={busy === d.id}
                onClick={() => void act(d.id, 'reject')}
                className="pixel-panel px-6 py-2 opacity-70"
              >
                Rechazar
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
