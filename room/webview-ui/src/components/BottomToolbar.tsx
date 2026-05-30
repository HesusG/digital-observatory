import type { WorkspaceFolder } from '../hooks/useExtensionMessages.js';

interface BottomToolbarProps {
  isEditMode: boolean;
  onOpenClaude: () => void;
  onToggleEditMode: () => void;
  isSettingsOpen: boolean;
  onToggleSettings: () => void;
  workspaceFolders: WorkspaceFolder[];
}

// Read-only public room: the pixel-agents extension toolbar (launch Claude,
// edit layout, settings) is not meaningful here, so render nothing. Props are
// kept so the App.tsx call site and its handlers stay wired (no unused locals).
export function BottomToolbar(_props: BottomToolbarProps) {
  return null;
}
