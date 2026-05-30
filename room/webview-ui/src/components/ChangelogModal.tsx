interface ChangelogModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentVersion: string;
}

// Upstream pixel-agents changelog — removed for this fork. Render nothing.
export function ChangelogModal(_props: ChangelogModalProps) {
  return null;
}
