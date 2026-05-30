/**
 * Translate digital-observatory agent events (from /api/events) into the
 * ServerMessages the pixel-office renderer already understands.
 *
 * The renderer animates "typing" vs "reading" by tool NAME (reading tools =
 * Read/Grep/Glob/WebFetch/WebSearch). We borrow that: Tess/Edu read, Carla/
 * Pablo write. Each agent maps to a fixed character id.
 */
import type { ServerMessage } from '../../../core/src/messages.js';
import { HESUS_LINES, MORENO_LINES } from '../office/engine/chatLines.js';

export const AGENT_IDS: Record<string, number> = {
  tess: 1,
  carla: 2,
  edu: 3,
  pablo: 4,
  moreno: 5,
  hesus: 6,
};

export const AGENT_ORDER = ['tess', 'carla', 'edu', 'pablo'] as const;

// Full cast seeded on connect (workers + bosses). Bosses get gold glow + crown;
// Hesus is WASD-controlled. displayName is shown above every character.
export interface SeedAgent {
  name: string;
  id: number;
  displayName: string;
  isBoss?: boolean;
  isPlayer?: boolean;
  palette?: number;
  hueShift?: number;
  chatLines?: string[];
}

export const SEED_AGENTS: SeedAgent[] = [
  { name: 'tess', id: 1, displayName: 'tess', palette: 4 },
  { name: 'carla', id: 2, displayName: 'carla', palette: 1 },
  { name: 'edu', id: 3, displayName: 'edu', palette: 2 },
  { name: 'pablo', id: 4, displayName: 'pablo', palette: 3 },
  {
    name: 'moreno',
    id: 5,
    displayName: 'Moreno',
    isBoss: true,
    palette: 0,
    hueShift: 35,
    chatLines: MORENO_LINES,
  },
  {
    name: 'hesus',
    id: 6,
    displayName: 'Hesus',
    isBoss: true,
    isPlayer: true,
    palette: 5,
    chatLines: HESUS_LINES,
  },
];

const READ_TOOL = 'Read'; // → reading animation
const WRITE_TOOL = 'Write'; // → typing animation

export interface ApiEvent {
  seq: number;
  agent: string;
  event_type: string;
  payload?: Record<string, unknown> | null;
  platform?: string | null;
  lang?: string | null;
  item_url?: string | null;
}

function clip(v: unknown, n = 48): string {
  return String(v ?? '').slice(0, n);
}

function label(ev: ApiEvent): string {
  const p = ev.payload ?? {};
  const title = p.title ? ` — ${clip(p.title, 40)}` : '';
  const pl = ev.platform ? ` ${ev.platform}` : '';
  switch (ev.event_type) {
    case 'tess.scored':
      return `Scoring${title}`;
    case 'tess.skipped':
      return `Skip: ${clip(p.skip_reason)}`;
    case 'carla.drafted':
      return `Drafting${pl}/${ev.lang ?? ''}`;
    case 'edu.approved':
      return `Approved${pl}`;
    case 'edu.revise':
      return `Revise: ${clip(p.reasoning)}`;
    case 'edu.reject':
      return `Reject: ${clip(p.reasoning)}`;
    case 'pablo.published':
      return `Published${pl} ✅`;
    case 'pablo.failed':
      return `Failed: ${clip(p.error)}`;
    default:
      return ev.event_type;
  }
}

export interface Translated {
  /** Messages to apply immediately (status + tool start, plus terminal status). */
  start: ServerMessage[];
  /** The matching tool-done message, applied after a delay (live) or at once (replay). */
  done: ServerMessage | null;
}

/** Translate one API event into renderer messages. Returns empty start/done for
 *  events with no visual (e.g. user.skipped). */
export function translateEvent(ev: ApiEvent): Translated {
  // User actions: attribute the "approve" to Pablo (the publisher) waking up.
  if (ev.agent === 'user') {
    if (ev.event_type === 'user.approved') {
      return { start: [{ type: 'agentStatus', id: AGENT_IDS.pablo, status: 'active' }], done: null };
    }
    return { start: [], done: null };
  }

  const id = AGENT_IDS[ev.agent];
  if (!id) return { start: [], done: null };

  const readLike = ev.agent === 'tess' || ev.agent === 'edu';
  const toolName = readLike ? READ_TOOL : WRITE_TOOL;
  const toolId = `e${ev.seq}`;

  const start: ServerMessage[] = [
    { type: 'agentStatus', id, status: 'active' },
    { type: 'agentToolStart', id, toolId, status: label(ev), toolName },
  ];
  if (ev.event_type === 'pablo.published') {
    start.push({ type: 'agentStatus', id, status: 'waiting' });
  }

  return { start, done: { type: 'agentToolDone', id, toolId } };
}
