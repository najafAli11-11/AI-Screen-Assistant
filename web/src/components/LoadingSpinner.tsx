interface LoadingSpinnerProps {
  text: string;
}

export function LoadingSpinner({ text }: LoadingSpinnerProps) {
  return (
    <div className="loading-container">
      <div className="loading-spinner">
        <div className="ring" />
        <div className="ring-accent" />
        <div className="ring-inner" />
      </div>
      <span className="loading-text">{text}</span>
      <div className="loading-dots">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
