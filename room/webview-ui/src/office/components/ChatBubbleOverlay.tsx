import { useEffect, useState } from 'react';

import { CHARACTER_SITTING_OFFSET_PX, TOOL_OVERLAY_VERTICAL_OFFSET } from '../../constants.js';
import type { OfficeState } from '../engine/officeState.js';
import { CharacterState, TILE_SIZE } from '../types.js';

interface ChatBubbleOverlayProps {
  officeState: OfficeState;
  agents: number[];
  containerRef: React.RefObject<HTMLDivElement | null>;
  zoom: number;
  panRef: React.RefObject<{ x: number; y: number }>;
}

// DOM overlay that draws ambient chat bubbles to the RIGHT of any character
// whose chatText is set (the boss characters). Mirrors ToolOverlay's screen math.
export function ChatBubbleOverlay({
  officeState,
  agents,
  containerRef,
  zoom,
  panRef,
}: ChatBubbleOverlayProps) {
  const [, setTick] = useState(0);
  useEffect(() => {
    let rafId = 0;
    const tick = () => {
      setTick((n) => n + 1);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, []);

  const el = containerRef.current;
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const canvasW = Math.round(rect.width * dpr);
  const canvasH = Math.round(rect.height * dpr);
  const layout = officeState.getLayout();
  const mapW = layout.cols * TILE_SIZE * zoom;
  const mapH = layout.rows * TILE_SIZE * zoom;
  const deviceOffsetX = Math.floor((canvasW - mapW) / 2) + Math.round(panRef.current.x);
  const deviceOffsetY = Math.floor((canvasH - mapH) / 2) + Math.round(panRef.current.y);

  return (
    <>
      {agents.map((id) => {
        const ch = officeState.characters.get(id);
        if (!ch || !ch.chatText) return null;
        const sittingOffset = ch.state === CharacterState.TYPE ? CHARACTER_SITTING_OFFSET_PX : 0;
        // Right of the character, roughly at head height.
        const screenX = (deviceOffsetX + ch.x * zoom) / dpr + 18;
        const screenY =
          (deviceOffsetY + (ch.y + sittingOffset - TOOL_OVERLAY_VERTICAL_OFFSET) * zoom) / dpr;
        return (
          <div
            key={id}
            className="absolute pixel-panel px-6 py-3 text-sm whitespace-nowrap pointer-events-none"
            style={{ left: screenX, top: screenY, zIndex: 43 }}
          >
            {ch.chatText}
          </div>
        );
      })}
    </>
  );
}
