// Left navigation rail for the Room shell. The Room is no longer a binary
// Oficina|Bandeja toggle but a management hub: this rail hosts the active
// sections and previews the upcoming ones (disabled) so the structure is clear.
// Only 'oficina' and 'bandeja' are functional today (subsystema E0 — no new
// features); the rest land in later phases (C, RAG, Plan, etc.).

export type RoomSection = 'oficina' | 'bandeja';

export const SIDEBAR_WIDTH = 190;

interface NavItem {
  id: string;
  emoji: string;
  label: string;
  enabled: boolean;
}

const SECTIONS: NavItem[] = [
  { id: 'oficina', emoji: '🏢', label: 'Oficina', enabled: true },
  { id: 'bandeja', emoji: '📥', label: 'Bandeja', enabled: true },
  { id: 'videos', emoji: '🎬', label: 'Videos & Guiones', enabled: false },
  { id: 'guias', emoji: '📚', label: 'Guías & Mentoring', enabled: false },
  { id: 'rag', emoji: '💬', label: 'Preguntar', enabled: false },
  { id: 'plan', emoji: '🗓️', label: 'Plan semanal', enabled: false },
];

interface RoomSidebarProps {
  section: RoomSection;
  onSelect: (section: RoomSection) => void;
}

export function RoomSidebar({ section, onSelect }: RoomSidebarProps) {
  return (
    <nav
      aria-label="Secciones del Room"
      className="absolute top-0 left-0 bottom-0 z-50 flex flex-col gap-2 bg-bg-dark border-r-2 border-border overflow-y-auto"
      style={{ width: SIDEBAR_WIDTH, padding: 10 }}
    >
      <div
        className="text-xs text-text-muted uppercase px-8 py-6"
        style={{ letterSpacing: 1 }}
      >
        Observatorio
      </div>

      {SECTIONS.map((item) => {
        const base =
          'text-left px-10 py-8 text-sm flex items-center gap-6 rounded-none border-2';

        if (!item.enabled) {
          return (
            <div
              key={item.id}
              className={`${base} border-transparent text-text-muted opacity-40 cursor-not-allowed`}
              title="Próximamente"
              aria-disabled="true"
            >
              <span>{item.emoji}</span>
              <span className="flex-1">{item.label}</span>
              <span className="text-2xs">pronto</span>
            </div>
          );
        }

        const active = item.id === section;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id as RoomSection)}
            aria-current={active ? 'page' : undefined}
            className={`${base} ${
              active
                ? 'border-border bg-active-bg text-accent-bright'
                : 'border-transparent text-text hover:text-accent-bright'
            }`}
          >
            <span>{item.emoji}</span>
            <span className="flex-1">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
