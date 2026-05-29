interface MigrationNoticeProps {
  onDismiss: () => void;
}

// Upstream "we reset your layout, thanks for using Pixel Agents" apology —
// not relevant to this fork. Render nothing.
export function MigrationNotice(_props: MigrationNoticeProps) {
  return null;
}
