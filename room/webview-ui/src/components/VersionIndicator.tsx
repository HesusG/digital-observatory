interface VersionIndicatorProps {
  currentVersion: string;
  lastSeenVersion: string;
  onDismiss: () => void;
  onOpenChangelog: () => void;
}

// Repurposed for this fork: instead of the upstream version badge / "what's
// new" / changelog launcher, show the office's own title banner.
export function VersionIndicator(_props: VersionIndicatorProps) {
  return (
    <div className="absolute top-10 left-1/2 -translate-x-1/2 z-20 pixel-panel px-14 py-7 select-none pointer-events-none flex flex-col items-center text-center gap-2">
      <span className="text-3xl text-accent-bright leading-none">🏢 Mi oficina de marketing</span>
      <span className="text-base opacity-60 leading-none">Tess · Carla · Edu · Pablo</span>
    </div>
  );
}
