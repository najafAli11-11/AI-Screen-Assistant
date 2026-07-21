interface CaptionOverlayProps {
  texts: string[];
  active: boolean;
}

export function CaptionOverlay({ texts, active }: CaptionOverlayProps) {
  if (!active || texts.length === 0) return null;

  return (
    <aside className="caption-overlay" aria-live="polite">
      {texts.slice(-3).map((text, index) => (
        <p key={`${text}-${index}`}>{text}</p>
      ))}
    </aside>
  );
}
