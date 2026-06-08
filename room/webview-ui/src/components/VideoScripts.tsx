import { useCallback, useEffect, useState } from 'react';

interface DraftItem {
  id: string;
  metadata: Record<string, unknown>;
  document: string;
}

const PROFILE_META: Record<string, { emoji: string; name: string }> = {
  'tech-reviewer': { emoji: '🗞️', name: 'Tech Reviewer' },
  'tech-educator': { emoji: '📐', name: 'Tech Educator' },
  'linkedin-influencer': { emoji: '💼', name: 'LinkedIn Influencer' },
  promo: { emoji: '📚', name: 'Promo' },
};

const SCRIPT_KIND: Record<string, string> = {
  youtube_long: '🎬 Guion largo',
  youtube_short: '⚡ Guion short',
};

const isScript = (platform: unknown): boolean =>
  platform === 'youtube_long' || platform === 'youtube_short';

// "Videos & Guiones" section: lists generated YouTube SCRIPTS (subsistema C).
// Scripts have no auto-publish target (account youtube → Obsidian draft), so the
// actions are read/edit/skip/reject — no "publicar".
export function VideoScripts() {
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/drafts?status=awaiting-user&limit=100');
      const d = (await r.json()) as { items?: DraftItem[] };
      setDrafts((d.items ?? []).filter((it) => isScript(it.metadata?.platform)));
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

  return (
    <div className="absolute inset-0 flex flex-col bg-bg">
      <div className="shrink-0 border-b-2 border-border px-20 py-12 flex items-center gap-10">
        <div className="text-xl text-accent-bright">🎬 Videos & Guiones ({drafts.length})</div>
        <button
          onClick={() => void load()}
          className="pixel-panel px-10 py-4 text-sm hover:text-accent-bright"
          aria-label="Refrescar guiones"
        >
          ↻
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-20 py-16">
        {drafts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div className="text-5xl">🎬</div>
            <div className="text-lg text-text-muted">Sin guiones pendientes</div>
            <div className="font-read text-sm text-text-muted" style={{ maxWidth: 460 }}>
              Los perfiles tech-reviewer (shorts) y tech-educator (largos) generan guiones
              desde las noticias. Cuando el pipeline corra, aparecerán aquí.
            </div>
          </div>
        ) : (
          <div className="mx-auto flex flex-col gap-16" style={{ maxWidth: 820 }}>
            {drafts.map((d) => {
              const m = d.metadata as {
                platform?: string;
                lang?: string;
                item_title?: string;
                profile_id?: string;
              };
              const title = m.item_title || '(sin título)';
              const profile = m.profile_id ? PROFILE_META[m.profile_id] : undefined;
              const kind = m.platform ? (SCRIPT_KIND[m.platform] ?? m.platform) : '';
              const isEditing = editingId === d.id;
              return (
                <div key={d.id} className="pixel-panel flex flex-col">
                  {/* Cabecera: tipo de guion + perfil + destino */}
                  <div className="px-12 py-7 border-b-2 border-border flex items-center gap-6 bg-active-bg flex-wrap">
                    <span className="text-sm text-accent-bright shrink-0">{kind}</span>
                    {profile && (
                      <span className="text-sm text-text-muted shrink-0">
                        · {profile.emoji} {profile.name}
                      </span>
                    )}
                    <span className="text-sm text-text-muted shrink-0">→ ▶ YouTube · borrador</span>
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

                  {/* Guion */}
                  <div className="px-12 py-10 flex flex-col gap-6">
                    {isEditing ? (
                      <div className="flex flex-col gap-5">
                        <textarea
                          value={editingText}
                          onChange={(e) => setEditingText(e.target.value)}
                          className="font-read pixel-panel p-8 text-base w-full"
                          style={{ minHeight: 320, lineHeight: 1.6 }}
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
                            Guardar
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
                      <div
                        className="font-read text-base text-text whitespace-pre-wrap"
                        style={{ lineHeight: 1.65 }}
                      >
                        {d.document}
                      </div>
                    )}
                  </div>

                  {!isEditing && (
                    <div className="px-12 pb-12 flex gap-4">
                      <button
                        disabled={busy === d.id}
                        onClick={() => {
                          setEditingId(d.id);
                          setEditingText(d.document);
                        }}
                        className="flex-1 pixel-panel px-6 py-4 text-sm disabled:opacity-35 hover:text-accent-bright"
                      >
                        ✏️ Editar
                      </button>
                      <button
                        disabled={busy === d.id}
                        onClick={() => void act(d.id, 'skip')}
                        className="flex-1 pixel-panel px-6 py-4 text-sm disabled:opacity-35 hover:text-accent-bright"
                      >
                        ⏭️ Saltar
                      </button>
                      <button
                        disabled={busy === d.id}
                        onClick={() => void act(d.id, 'reject')}
                        className="flex-1 pixel-panel px-6 py-4 text-sm text-danger disabled:opacity-35 hover:bg-accent"
                      >
                        ❌ Rechazar
                      </button>
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
