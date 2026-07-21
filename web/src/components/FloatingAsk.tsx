import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { PictureInPicture2 } from 'lucide-react';

interface DocumentPictureInPicture {
  requestWindow(options?: { width?: number; height?: number }): Promise<Window>;
}

declare global {
  interface Window {
    documentPictureInPicture?: DocumentPictureInPicture;
  }
}

export const isFloatSupported = typeof window !== 'undefined' && Boolean(window.documentPictureInPicture);

const PIP_CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #0a0a0f;
    color: #e8e8f0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    height: 100vh;
    padding: 10px;
  }
  button {
    font: inherit;
    font-weight: 700;
    font-size: 16px;
    color: #ffffff;
    background: linear-gradient(135deg, #f97316, #ef4444);
    border: none;
    border-radius: 10px;
    padding: 14px 30px;
    cursor: pointer;
    width: 100%;
    transition: filter 0.2s ease;
  }
  button:hover:not(:disabled) { filter: brightness(1.15); }
  button:disabled { opacity: 0.4; cursor: default; }
  .pip-status { font-size: 13px; color: #7a7a8f; font-weight: 600; }
  .pip-status.listening { color: #f59e0b; }
`;

interface FloatingAskProps {
  canAsk: boolean;
  askLabel: string;
  statusText: string;
  isListening: boolean;
  onAsk: () => void;
}

export function FloatingAsk({ canAsk, askLabel, statusText, isListening, onAsk }: FloatingAskProps) {
  const [pipWindow, setPipWindow] = useState<Window | null>(null);
  const pipRef = useRef<Window | null>(null);

  const openFloat = useCallback(async () => {
    if (!window.documentPictureInPicture || pipRef.current) return;
    try {
      const win = await window.documentPictureInPicture.requestWindow({ width: 220, height: 120 });
      const style = win.document.createElement('style');
      style.textContent = PIP_CSS;
      win.document.head.appendChild(style);
      win.document.title = 'AI Ask';
      win.addEventListener('pagehide', () => {
        pipRef.current = null;
        setPipWindow(null);
      });
      pipRef.current = win;
      setPipWindow(win);
    } catch {
      // User denied or browser refused
    }
  }, []);

  useEffect(() => () => pipRef.current?.close(), []);

  let portal: ReactNode = null;
  if (pipWindow) {
    portal = createPortal(
      <>
        <button onClick={onAsk} disabled={!canAsk}>{askLabel}</button>
        <span className={`pip-status ${isListening ? 'listening' : ''}`}>{statusText}</span>
      </>,
      pipWindow.document.body,
    );
  }

  if (!isFloatSupported) return null;

  return (
    <>
      <button className="btn-ghost" onClick={openFloat} disabled={Boolean(pipWindow)} title="Open a small always-on-top Ask button">
        <PictureInPicture2 size={18} aria-hidden />
        {pipWindow ? 'Floating' : 'Float Ask'}
      </button>
      {portal}
    </>
  );
}
