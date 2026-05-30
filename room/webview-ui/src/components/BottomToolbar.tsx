import type { WorkspaceFolder } from '../hooks/useExtensionMessages.js';
import { Button } from './ui/Button.js';

interface BottomToolbarProps {
  isEditMode: boolean;
  onOpenClaude: () => void;
  onToggleEditMode: () => void;
  isSettingsOpen: boolean;
  onToggleSettings: () => void;
  workspaceFolders: WorkspaceFolder[];
}

// Read-only public room: expose ONLY the "Layout" toggle (customize the office).
// +Agent and Settings are intentionally not rendered. Only the two props this
// component uses are destructured; the rest remain in the interface (App.tsx
// still passes them) so there are no unused locals at the call site, and
// noUnusedParameters is satisfied because undestructured props don't count.
export function BottomToolbar({ isEditMode, onToggleEditMode }: BottomToolbarProps) {
  return (
    <div className="absolute bottom-10 left-10 z-20 flex items-center gap-4 pixel-panel p-4">
      <Button
        variant={isEditMode ? 'active' : 'default'}
        onClick={onToggleEditMode}
        title="Edit office layout"
      >
        Layout
      </Button>
    </div>
  );
}
