import { isBrowserRuntime } from '../runtime.js';
import { PostMessageTransport } from './postMessageTransport.js';
import { SseTransport } from './sseTransport.js';
import type { MessageTransport } from './types.js';

function createTransport(): MessageTransport {
  if (!isBrowserRuntime) {
    return new PostMessageTransport();
  }
  // Standalone browser: feed the office from the digital-observatory event log
  // (REST history + SSE live) served by the same FastAPI host.
  return new SseTransport();
}

/** Singleton transport instance. Import this everywhere instead of vscodeApi. */
export const transport: MessageTransport = createTransport();
export type { MessageTransport } from './types.js';
