/**
 * SseTransport — feeds the pixel-office renderer from the digital-observatory
 * event log instead of Claude Code transcripts.
 *
 * On the first subscription it:
 *   1. loads + emits the office assets (reusing browserMock's loaders),
 *   2. creates the fixed agent cast (Tess/Carla/Edu/Pablo),
 *   3. replays history from GET /api/events,
 *   4. streams live events from GET /api/events/stream (SSE).
 *
 * The whole office engine and useExtensionMessages stay unmodified — everything
 * arrives through transport.onMessage, exactly like the WebSocket transport.
 */
import type { ClientMessage, ServerMessage } from '../../../core/src/messages.js';
import { assetLoadMessages, loadAssets } from '../browserMock.js';
import { AGENT_IDS, AGENT_ORDER, type ApiEvent, translateEvent } from './eventTranslate.js';
import type { MessageTransport } from './types.js';

const LIVE_DONE_DELAY_MS = 2500; // how long a character animates per live event

export class SseTransport implements MessageTransport {
  private handlers: Array<(msg: ServerMessage) => void> = [];
  private es: EventSource | null = null;
  private started = false;
  private disposed = false;
  private readonly base: string;

  constructor(base = '') {
    this.base = base.replace(/\/$/, '');
  }

  onMessage(handler: (message: ServerMessage) => void): () => void {
    this.handlers.push(handler);
    if (!this.started) {
      this.started = true;
      void this.start();
    }
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  // The read-only room never needs to talk back to a host.
  send(_message: ClientMessage): void {}

  dispose(): void {
    this.disposed = true;
    this.es?.close();
    this.es = null;
    this.handlers = [];
  }

  private emit(msg: ServerMessage): void {
    for (const handler of this.handlers) handler(msg);
  }

  private async start(): Promise<void> {
    // 1. Assets (PNG-decoded in-browser for the static build).
    try {
      const payload = await loadAssets();
      for (const msg of assetLoadMessages(payload)) this.emit(msg as ServerMessage);
    } catch (e) {
      console.error('[SSE] asset load failed', e);
    }
    if (this.disposed) return;

    // 2. Fixed cast.
    for (const name of AGENT_ORDER) {
      this.emit({ type: 'agentCreated', id: AGENT_IDS[name], folderName: name });
    }

    // 3. History (replay): apply start + done at once so agents settle idle.
    let lastSeq = 0;
    try {
      const res = await fetch(`${this.base}/api/events?since_seq=0&limit=1000`);
      const data = (await res.json()) as { events?: ApiEvent[] };
      for (const ev of data.events ?? []) {
        lastSeq = Math.max(lastSeq, ev.seq);
        const t = translateEvent(ev);
        t.start.forEach((m) => this.emit(m));
        if (t.done) this.emit(t.done);
      }
    } catch (e) {
      console.error('[SSE] history fetch failed', e);
    }
    if (this.disposed) return;

    // 4. Live: animate each event for a beat, then mark its tool done.
    this.es = new EventSource(`${this.base}/api/events/stream?since_seq=${lastSeq}`);
    this.es.onmessage = (e: MessageEvent) => {
      let ev: ApiEvent;
      try {
        ev = JSON.parse(e.data as string) as ApiEvent;
      } catch {
        return;
      }
      const t = translateEvent(ev);
      t.start.forEach((m) => this.emit(m));
      if (t.done) {
        const done = t.done;
        setTimeout(() => {
          if (!this.disposed) this.emit(done);
        }, LIVE_DONE_DELAY_MS);
      }
    };
  }
}
