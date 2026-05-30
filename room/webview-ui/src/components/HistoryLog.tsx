import { useEffect, useRef, useState } from 'react';

// Always-visible right-side panel showing the day's agent activity, read
// straight from the observatory event log (GET /api/events + SSE stream).
// Independent of the office renderer — it just narrates what happened.

interface ApiEvent {
  seq: number;
  ts: string;
  agent: string;
  event_type: string;
  payload?: Record<string, unknown> | null;
  platform?: string | null;
  lang?: string | null;
}

const AGENT_EMOJI: Record<string, string> = {
  tess: '🔭',
  carla: '✍️',
  edu: '📐',
  pablo: '📤',
  user: '👤',
};

function clip(v: unknown, n = 46): string {
  const s = String(v ?? '');
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function describe(ev: ApiEvent): string {
  const p = ev.payload ?? {};
  const pl = ev.platform ? ` ${ev.platform}` : '';
  switch (ev.event_type) {
    case 'tess.scored':
      return `puntuó “${clip(p.title, 32)}” (${String(p.teacher_relevance ?? '?')}/10)`;
    case 'tess.skipped':
      return `descartó: ${clip(p.skip_reason)}`;
    case 'carla.drafted':
      return `redactó${pl}/${ev.lang ?? ''}`;
    case 'edu.approved':
      return `aprobó${pl} ✅`;
    case 'edu.revise':
      return `pidió revisión: ${clip(p.reasoning, 30)}`;
    case 'edu.reject':
      return `rechazó: ${clip(p.reasoning, 30)}`;
    case 'pablo.published':
      return `publicó${pl} 🚀`;
    case 'pablo.failed':
      return `falló al publicar: ${clip(p.error, 28)}`;
    case 'user.approved':
      return `aprobaste un borrador`;
    case 'user.skipped':
      return `omitiste un borrador`;
    default:
      return ev.event_type;
  }
}

function dayKey(ts: string): string {
  // ts is ISO UTC; show just the date portion.
  return ts.slice(0, 10);
}

function timeLabel(ts: string): string {
  return ts.slice(11, 16); // HH:MM
}

export function HistoryLog() {
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const seenRef = useRef<Set<number>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    function add(incoming: ApiEvent[]) {
      const fresh = incoming.filter((e) => !seenRef.current.has(e.seq));
      if (fresh.length === 0) return;
      fresh.forEach((e) => seenRef.current.add(e.seq));
      setEvents((prev) => [...prev, ...fresh].sort((a, b) => a.seq - b.seq));
    }

    (async () => {
      try {
        const res = await fetch('/api/events?since_seq=0&limit=500');
        const data = (await res.json()) as { events?: ApiEvent[]; latest_seq?: number };
        if (cancelled) return;
        add(data.events ?? []);
        const last = data.latest_seq ?? 0;
        es = new EventSource(`/api/events/stream?since_seq=${last}`);
        es.onmessage = (e: MessageEvent) => {
          try {
            add([JSON.parse(e.data as string) as ApiEvent]);
          } catch {
            /* ignore malformed */
          }
        };
      } catch {
        /* offline; panel stays empty */
      }
    })();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, []);

  // Auto-scroll to the newest entry.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events]);

  let lastDay = '';

  return (
    <div className="absolute top-0 right-0 bottom-0 w-80 z-20 pixel-panel flex flex-col border-l-2 border-border">
      <div className="px-12 py-8 text-lg text-accent-bright border-b border-border shrink-0">
        📋 Historial del día
      </div>
      <div ref={listRef} className="flex-1 overflow-y-auto px-10 py-8 flex flex-col gap-3">
        {events.length === 0 && (
          <div className="text-sm opacity-50">Sin actividad todavía…</div>
        )}
        {events.map((ev) => {
          const d = dayKey(ev.ts);
          const showDay = d !== lastDay;
          lastDay = d;
          return (
            <div key={ev.seq}>
              {showDay && (
                <div className="text-sm text-accent-bright opacity-80 mt-6 mb-2">{d}</div>
              )}
              <div className="text-sm leading-snug flex gap-4">
                <span className="opacity-40 shrink-0">{timeLabel(ev.ts)}</span>
                <span>
                  <span className="mr-2">{AGENT_EMOJI[ev.agent] ?? '•'}</span>
                  <span className="text-accent-bright">{ev.agent}</span> {describe(ev)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
