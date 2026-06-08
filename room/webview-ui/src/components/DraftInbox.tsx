import { useCallback, useEffect, useState } from 'react';

interface DraftItem {
  id: string;
  metadata: Record<string, unknown>;
  document: string;
}

// Display metadata for the content profiles (subsistema A) and account aliases.
// Used to render the "destino" strip so it's clear which profile/account a draft
// is headed to. Unknown ids fall back gracefully.
const PROFILE_META: Record<string, { emoji: string; name: string }> = {
  'tech-reviewer': { emoji: '🗞️', name: 'Tech Reviewer' },
  'tech-educator': { emoji: '📐', name: 'Tech Educator' },
  'linkedin-influencer': { emoji: '💼', name: 'LinkedIn Influencer' },
  promo: { emoji: '📚', name: 'Promo' },
};

const ACCOUNT_LABEL: Record<string, string> = {
  x: '𝕏 X',
  linkedin: 'in · LinkedIn',
  bluesky: '🦋 Bluesky',
  youtube: '▶ YouTube',
};

// Approval inbox: lists drafts in status "awaiting-user" as a responsive grid of
// compact, scannable cards. Approve / edit (inline) / skip / reject via /api/drafts.
export function DraftInbox() {
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showFolders, setShowFolders] = useState(false);
  const [available, setAvailable] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
      // YouTube scripts live in the "Videos & Guiones" section, not here.
      const isScript = (p: unknown) => p === 'youtube_long' || p === 'youtube_short';
      setDrafts((d.items ?? []).filter((it) => !isScript(it.metadata?.platform)));
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
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {processing ? 'Procesando notas…' : busy ? 'Procesando acción…' : ''}
      </div>

      {/* HEADER BAR — actions kept on the left so they don't collide with the
          top-right Oficina|Bandeja tab bar. */}
      <div
        className="shrink-0 border-b-2 border-border px-20 py-12 flex items-center gap-10 flex-wrap"
      >
        <div className="text-xl text-accent-bright">
          📥 Bandeja de aprobación ({drafts.length})
        </div>
        <div className="flex gap-5">
          <button
            onClick={processNotes}
            disabled={processing}
            className="pixel-panel px-10 py-4 text-sm disabled:opacity-35 hover:text-accent-bright"
            aria-label="Procesar notas de Obsidian"
            aria-busy={processing}
          >
            {processing ? 'Procesando…' : '📝 Procesar notas'}
          </button>
          <button
            onClick={() => void load()}
            className="pixel-panel px-10 py-4 text-sm hover:text-accent-bright"
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
            className="pixel-panel px-10 py-4 text-sm hover:text-accent-bright"
            aria-expanded={showFolders}
            aria-label={`${showFolders ? 'Cerrar' : 'Abrir'} selector de carpetas`}
          >
            📁 Carpetas
          </button>
        </div>
      </div>

      {/* FOLDER PICKER */}
      {showFolders && (
        <div className="shrink-0 border-b-2 border-border px-20 py-12">
          <div className="pixel-panel p-12 flex flex-col gap-5 max-w-700">
            <div className="text-base text-accent-bright">📁 Carpetas a procesar</div>
            <div className="text-sm text-text-muted">
              Marca las carpetas de Obsidian que se procesarán al pulsar “Procesar notas”.
            </div>
            {available.length === 0 && (
              <div className="text-sm text-text-muted">No se encontraron carpetas en el vault.</div>
            )}
            <div className="flex flex-col gap-4 max-h-260 overflow-y-auto">
              {available.map((f) => (
                <div key={f} className="text-sm flex items-center gap-5">
                  <input
                    id={`folder-${f}`}
                    type="checkbox"
                    checked={selected.includes(f)}
                    onChange={() => void toggleFolder(f)}
                    className="w-18 h-18 shrink-0"
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

      {/* CARD GRID */}
      <div className="flex-1 overflow-y-auto px-20 py-16">
        {drafts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div className="text-5xl">📭</div>
            <div className="text-lg text-text-muted">Sin borradores pendientes</div>
            <div className="text-sm text-text-muted">
              Usa <span className="text-accent-bright">📝 Procesar notas</span> para generar borradores desde Obsidian.
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-1100 grid grid-cols-1 lg:grid-cols-2 gap-16">
            {drafts.map((d) => {
              const m = d.metadata as {
                platform?: string;
                lang?: string;
                item_title?: string;
                edu_reasoning?: string;
                profile_id?: string;
                account?: string;
              };
              const title = m.item_title || '(sin título)';
              const profile = m.profile_id ? PROFILE_META[m.profile_id] : undefined;
              // Prefer the explicit account alias; fall back to platform for
              // older drafts created before the profiles layer.
              const accountKey = m.account || m.platform || '';
              const accountLabel = accountKey ? (ACCOUNT_LABEL[accountKey] ?? accountKey) : '';
              const isEditing = editingId === d.id;
              const isExpanded = expandedId === d.id;
              return (
                <div key={d.id} className="pixel-panel flex flex-col">
                  {/* Destino: perfil → cuenta. Lo más importante de un vistazo. */}
                  <div className="px-12 py-7 border-b-2 border-border flex items-center gap-6 bg-active-bg">
                    {profile && (
                      <span className="text-sm text-accent-bright shrink-0">
                        {profile.emoji} {profile.name}
                      </span>
                    )}
                    {profile && accountLabel && <span className="text-sm text-text-muted">→</span>}
                    {accountLabel && <span className="text-sm text-text shrink-0">{accountLabel}</span>}
                    {m.lang && (
                      <span className="ml-auto pixel-panel px-5 py-2 text-2xs text-text-muted uppercase">
                        {m.lang}
                      </span>
                    )}
                  </div>
                  {/* Título de la fuente */}
                  <div className="px-12 py-9 border-b-2 border-border">
                    <div className="font-read text-base text-text leading-snug">{title}</div>
                  </div>

                  {/* Body */}
                  <div className="px-12 py-10 flex flex-col gap-6 flex-1">
                    {isEditing ? (
                      <div className="flex flex-col gap-5">
                        <label htmlFor={`edit-${d.id}`} className="text-sm text-text-muted">
                          Editar contenido
                        </label>
                        <textarea
                          id={`edit-${d.id}`}
                          value={editingText}
                          onChange={(e) => setEditingText(e.target.value)}
                          className="pixel-panel p-8 text-base w-full"
                          style={{ minHeight: 220, lineHeight: 1.5 }}
                          autoFocus
                        />
                        <div className="flex gap-4">
                          <button
                            disabled={busy === d.id || !editingText.trim()}
                            onClick={async () => {
                              await act(d.id, 'edit', { content: editingText });
                              setEditingId(null);
                              setEditingText('');
                            }}
                            className="pixel-panel bg-accent text-white px-10 py-4 text-sm disabled:opacity-35 hover:bg-accent-bright"
                          >
                            Guardar y publicar
                          </button>
                          <button
                            onClick={() => {
                              setEditingId(null);
                              setEditingText('');
                            }}
                            className="pixel-panel px-10 py-4 text-sm"
                          >
                            Cancelar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div
                          className="font-read text-base text-text whitespace-pre-wrap overflow-hidden"
                          style={
                            isExpanded
                              ? { lineHeight: 1.6 }
                              : { lineHeight: 1.6, maxHeight: 160 }
                          }
                        >
                          {d.document}
                        </div>
                        {d.document.length > 180 && (
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : d.id)}
                            className="text-2xs text-accent-bright self-start hover:underline"
                          >
                            {isExpanded ? '▲ Ver menos' : '▼ Ver todo'}
                          </button>
                        )}
                        {m.edu_reasoning && (
                          <div className="font-read pt-5 border-t border-border text-xs text-text-muted leading-relaxed">
                            <span className="text-accent-bright">Edu:</span> {m.edu_reasoning}
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Actions */}
                  {!isEditing && (
                    <div className="px-12 pb-12 flex flex-col gap-4">
                      <button
                        disabled={busy === d.id}
                        onClick={() => void act(d.id, 'approve')}
                        className="pixel-panel bg-accent text-white py-5 text-base disabled:opacity-35 hover:bg-accent-bright"
                        aria-label={`Aprobar y publicar borrador: ${title}`}
                      >
                        ✅ Aprobar y publicar
                      </button>
                      <div className="flex gap-4">
                        <button
                          disabled={busy === d.id}
                          onClick={() => {
                            setEditingId(d.id);
                            setEditingText(d.document);
                          }}
                          className="flex-1 pixel-panel px-6 py-4 text-sm disabled:opacity-35 hover:text-accent-bright"
                          aria-label={`Editar borrador: ${title}`}
                        >
                          ✏️ Editar
                        </button>
                        <button
                          disabled={busy === d.id}
                          onClick={() => void act(d.id, 'skip')}
                          className="flex-1 pixel-panel px-6 py-4 text-sm disabled:opacity-35 hover:text-accent-bright"
                          aria-label={`Saltar borrador: ${title}`}
                        >
                          ⏭️ Saltar
                        </button>
                        <button
                          disabled={busy === d.id}
                          onClick={() => void act(d.id, 'reject')}
                          className="flex-1 pixel-panel px-6 py-4 text-sm text-danger disabled:opacity-35 hover:bg-accent"
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
        )}
      </div>
    </div>
  );
}
