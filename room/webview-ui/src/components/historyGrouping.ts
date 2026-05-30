// Pure, DOM-free helpers for grouping history events by LOCAL day and time band.
// Kept separate from HistoryLog.tsx so they can be unit-tested with node:test.

export type Band = 'manana' | 'tarde' | 'noche';

export const BAND_ORDER: Band[] = ['manana', 'tarde', 'noche'];

export const BAND_LABEL: Record<Band, string> = {
  manana: '🌅 Mañana',
  tarde: '☀️ Tarde',
  noche: '🌙 Noche',
};

// Local hour bands: Mañana [6,12), Tarde [12,19), Noche [19,24) ∪ [0,6).
export function bandOf(date: Date): Band {
  const h = date.getHours();
  if (h >= 6 && h < 12) return 'manana';
  if (h >= 12 && h < 19) return 'tarde';
  return 'noche';
}

// Local YYYY-MM-DD (not UTC) so day boundaries match the viewer's clock.
export function localDayKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// Local HH:MM.
export function localTimeLabel(date: Date): string {
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function groupKey(day: string, band: Band): string {
  return `${day}|${band}`;
}
