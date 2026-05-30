import { useEffect, useMemo, useRef, useState } from 'react';

import {
  BAND_LABEL,
  BAND_ORDER,
  bandOf,
  groupKey,
  localDayKey,
  localTimeLabel,
} from './historyGrouping.js';
import type { Band } from './historyGrouping.js';

// Always-visible right-side panel showing the day's agent activity, read
// straight from the observatory event log (GET /api/events + SSE stream).
//
// NOTE: this app's Tailwind (v4) sets `--spacing: 1px` in index.css, so a class
// like `w-80` is 80px, NOT 320px. The panel's structural width is an explicit
// pixel constant used by inline style here AND by App.tsx to inset the office.
export const HISTORY_PANEL_WIDTH = 400;

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

// Order of the filter chips. Known agents; unknown agents are always shown.
const AGENTS = ['tess', 'carla', 'edu', 'pablo', 'user'];
const KNOWN_AGENTS = new Set(AGENTS);

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

interface BandGroup {
  band: Band;
  key: string;
  events: ApiEvent[];
}
interface DayGroup {
  day: string;
  bands: BandGroup[];
}

// Group events (assumed sorted by seq asc) into day -> band, in local time.
function groupByDayBand(events: ApiEvent[]): DayGroup[] {
  const days = new Map<string, Map<Band, ApiEvent[]>>();
  for (const ev of events) {
    const d = new Date(ev.ts);
    const day = localDayKey(d);
    const band = bandOf(d);
    let bands = days.get(day);
    if (!bands) {
      bands = new Map<Band, ApiEvent[]>();
      days.set(day, bands);
    }
    const arr = bands.get(band);
    if (arr) arr.push(ev);
    else bands.set(band, [ev]);
  }
  return [...days.keys()].sort().map((day) => ({
    day,
    bands: BAND_ORDER.filter((b) => days.get(day)!.has(b)).map((band) => ({
      band,
      key: groupKey(day, band),
      events: days.get(day)!.get(band)!,
    })),
  }));
}

export function HistoryLog() {
  const [events, setEvents] = useState<ApiEvent[]>([]);
  const seenRef = useRef<Set<number>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);

  // Agent filter: set of ACTIVE agents (all on by default).
  const [activeAgents, setActiveAgents] = useState<Set<string>>(() => new Set(AGENTS));
  // Collapse overrides per group key; default-open rule is `day === today`.
  const [openOverride, setOpenOverride] = useState<Record<string, boolean>>({});

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

  const visibleEvents = useMemo(
    () => events.filter((e) => !KNOWN_AGENTS.has(e.agent) || activeAgents.has(e.agent)),
    [events, activeAgents],
  );
  const dayGroups = useMemo(() => groupByDayBand(visibleEvents), [visibleEvents]);
  const todayKey = localDayKey(new Date());

  // Auto-scroll to the newest entry when events change.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visibleEvents]);

  function toggleAgent(agent: string) {
    setActiveAgents((prev) => {
      const next = new Set(prev);
      if (next.has(agent)) next.delete(agent);
      else next.add(agent);
      return next;
    });
  }

  function isOpen(day: string, key: string): boolean {
    return openOverride[key] ?? day === todayKey;
  }
  function toggleGroup(day: string, key: string) {
    const current = isOpen(day, key);
    setOpenOverride((prev) => ({ ...prev, [key]: !current }));
  }

  return (
    <div
      className="absolute top-0 right-0 bottom-0 z-20 pixel-panel flex flex-col border-l-2 border-border"
      style={{ width: HISTORY_PANEL_WIDTH }}
    >
      <div className="px-12 py-8 text-lg text-accent-bright border-b border-border shrink-0">
        📋 Historial del día
      </div>

      {/* Agent filter chips */}
      <div className="px-10 py-6 flex flex-wrap gap-3 border-b border-border shrink-0">
        {AGENTS.map((agent) => {
          const on = activeAgents.has(agent);
          return (
            <button
              key={agent}
              onClick={() => toggleAgent(agent)}
              title={on ? `Ocultar ${agent}` : `Mostrar ${agent}`}
              className={
                'pixel-panel px-6 py-2 text-sm cursor-pointer flex items-center gap-2 ' +
                (on ? 'text-text' : 'opacity-40')
              }
            >
              <span>{AGENT_EMOJI[agent] ?? '•'}</span>
              <span className="text-accent-bright">{agent}</span>
            </button>
          );
        })}
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto px-10 py-8 flex flex-col gap-3">
        {dayGroups.length === 0 && (
          <div className="text-sm opacity-50">Sin actividad todavía…</div>
        )}
        {dayGroups.map((dg) => (
          <div key={dg.day} className="flex flex-col gap-2">
            <div className="text-sm text-accent-bright opacity-80 mt-4 mb-1">{dg.day}</div>
            {dg.bands.map((bg) => {
              const open = isOpen(dg.day, bg.key);
              return (
                <div key={bg.key} className="flex flex-col">
                  <button
                    onClick={() => toggleGroup(dg.day, bg.key)}
                    className="flex items-center gap-3 text-sm text-text py-2 cursor-pointer select-none hover:text-accent-bright"
                  >
                    <span className="opacity-70 w-8 inline-block">{open ? '▾' : '▸'}</span>
                    <span>{BAND_LABEL[bg.band]}</span>
                    <span className="opacity-40">({bg.events.length})</span>
                  </button>
                  {open && (
                    <div className="flex flex-col gap-3 pl-10 pb-2">
                      {bg.events.map((ev) => (
                        <div key={ev.seq} className="text-sm leading-snug flex gap-4">
                          <span className="opacity-40 shrink-0">
                            {localTimeLabel(new Date(ev.ts))}
                          </span>
                          <span>
                            <span className="mr-2">{AGENT_EMOJI[ev.agent] ?? '•'}</span>
                            <span className="text-accent-bright">{ev.agent}</span> {describe(ev)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
