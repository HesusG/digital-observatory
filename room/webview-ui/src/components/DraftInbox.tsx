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
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');

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
    <div className="absolute inset-0 flex flex-col bg-bg">
      {/* Screen-reader status for async actions */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {processing ? 'Procesando notas…' : busy ? 'Procesando acción…' : ''}
      </div>

      {/* HEADER */}
      <div className="shrink-0 border-b-2 border-border px-16 py-12 flex items-center justify-between gap-8 flex-wrap">
        <div className="text-lg text-accent-bright">
          📥 Bandeja de aprobación ({drafts.length})
        </div>
        <div className="flex gap-4">
          <button
            onClick={processNotes}
            disabled={processing}
            className="pixel-panel px-8 py-3 text-sm disabled:opacity-35"
            aria-label="Procesar notas de Obsidian"
            aria-busy={processing}
          >
            {processing ? 'Procesando…' : '📝 Procesar notas'}
          </button>
          <button
            onClick={() => void load()}
            className="pixel-panel px-8 py-3 text-sm"
            aria-label="Refrescar bandeja"
          >
            ↻
          </button>
          <button
            onClick={() => {
              const next = !showFolders;
              setShowFolders(next);
              if (next) void loadFolders();
            }}
            className="pixel-panel px-8 py-3 text-sm"
            aria-expanded={showFolders}
            aria-label={`${showFolders ? 'Cerrar' : 'Abrir'} selector de carpetas`}
          >
            📁 Carpetas
          </button>
        </div>
      </div>

      {/* FOLDER PICKER (collapsible) */}
      {showFolders && (
        <div className="shrink-0 border-b-2 border-border px-16 py-10">
          <div className="pixel-panel p-10 flex flex-col gap-4 max-w-320">
            <div className="text-sm text-accent-bright">📁 Carpetas a procesar</div>
            <div className="text-2xs text-text-muted">
              Marca las carpetas de Obsidian que se procesarán al pulsar “Procesar notas”.
            </div>
            {available.length === 0 && (
              <div className="text-2xs text-text-muted">No se encontraron carpetas en el vault.</div>
            )}
            <div className="flex flex-col gap-3 max-h-200 overflow-y-auto">
              {available.map((f) => (
                <div key={f} className="text-sm flex items-center gap-4">
                  <input
                    id={`folder-${f}`}
                    type="checkbox"
                    checked={selected.includes(f)}
                    onChange={() => void toggleFolder(f)}
                    className="w-16 h-16 shrink-0"
                  />
                  <label htmlFor={`folder-${f}`} className="cursor-pointer hover:text-accent-bright">
                    {f}
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SCROLLABLE CARD AREA */}
      <div className="flex-1 overflow-y-auto px-16 py-12 flex flex-col items-center gap-10">
        {drafts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4">
            <div className="text-4xl">📭</div>
            <div className="text-base text-text-muted">Sin borradores pendientes</div>
            <div className="text-2xs text-text-muted">
              Usa <span className="text-accent-bright">📝 Procesar notas</span> para generar borradores desde Obsidian.
            </div>
          </div>
        )}

        {drafts.map((d) => {
          const m = d.metadata as {
            platform?: string;
            lang?: string;
            item_title?: string;
            edu_reasoning?: string;
          };
          const title = m.item_title || '(sin título)';
          const isBlog = m.platform === 'blog';
          const isEditing = editingId === d.id;
          return (
            <div key={d.id} className="pixel-panel w-full max-w-320 flex flex-col">
              {/* Card header: title + badges */}
              <div className="px-10 py-8 border-b-2 border-border flex items-center justify-between gap-6">
                <div className="text-sm text-accent-bright">{title}</div>
                <div className="flex gap-3 shrink-0">
                  <span className="pixel-panel px-4 py-1 text-2xs text-text-muted">{m.platform}</span>
                  <span className="pixel-panel px-4 py-1 text-2xs text-text-muted">{m.lang}</span>
                </div>
              </div>

              {/* Card body */}
              <div className="px-10 py-8 flex flex-col gap-6">
                {isEditing ? (
                  <div className="flex flex-col gap-4">
                    <label htmlFor={`edit-${d.id}`} className="text-2xs text-text-muted">
                      Editar contenido
                    </label>
                    <textarea
                      id={`edit-${d.id}`}
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      className="pixel-panel p-6 text-sm w-full"
                      style={{ minHeight: 160, lineHeight: 1.4 }}
                      autoFocus
                    />
                    <div className="flex gap-3">
                      <button
                        disabled={busy === d.id || !editingText.trim()}
                        onClick={async () => {
                          await act(d.id, 'edit', { content: editingText });
                          setEditingId(null);
                          setEditingText('');
                        }}
                        className="pixel-panel bg-accent text-white px-8 py-3 text-sm disabled:opacity-35"
                      >
                        Guardar y publicar
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(null);
                          setEditingText('');
                        }}
                        className="pixel-panel px-8 py-3 text-sm"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div
                      className="text-sm whitespace-pre-wrap"
                      style={isBlog ? { maxHeight: 200, overflowY: 'auto' } : undefined}
                    >
                      {d.document}
                    </div>
                    {m.edu_reasoning && (
                      <div className="pt-4 border-t border-border text-2xs text-text-muted">
                        <span className="text-accent-bright">Edu:</span> {m.edu_reasoning}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Card actions */}
              {!isEditing && (
                <div className="px-10 pb-8 flex flex-col gap-4">
                  <button
                    disabled={busy === d.id}
                    onClick={() => void act(d.id, 'approve')}
                    className="pixel-panel bg-accent text-white py-4 text-sm disabled:opacity-35 hover:bg-accent-bright"
                    aria-label={`Aprobar y publicar borrador: ${title}`}
                  >
                    ✅ Aprobar y publicar
                  </button>
                  <div className="flex gap-3">
                    <button
                      disabled={busy === d.id}
                      onClick={() => {
                        setEditingId(d.id);
                        setEditingText(d.document);
                      }}
                      className="flex-1 pixel-panel px-6 py-3 text-sm disabled:opacity-35"
                      aria-label={`Editar borrador: ${title}`}
                    >
                      ✏️ Editar
                    </button>
                    <button
                      disabled={busy === d.id}
                      onClick={() => void act(d.id, 'skip')}
                      className="flex-1 pixel-panel px-6 py-3 text-sm disabled:opacity-35"
                      aria-label={`Saltar borrador: ${title}`}
                    >
                      ⏭️ Saltar
                    </button>
                    <button
                      disabled={busy === d.id}
                      onClick={() => void act(d.id, 'reject')}
                      className="flex-1 pixel-panel px-6 py-3 text-sm text-danger disabled:opacity-35"
                      aria-label={`Rechazar borrador: ${title}`}
                    >
                      ❌ Rechazar
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
