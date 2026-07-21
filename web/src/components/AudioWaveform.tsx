import { useEffect, useRef } from 'react';

interface AudioWaveformProps {
  isRecording: boolean;
}

const BAR_COUNT = 32;
const BAR_WIDTH = 3;
const BAR_GAP = 2;
const CANVAS_HEIGHT = 48;

export function AudioWaveform({ isRecording }: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<number>(0);
  const phaseRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const totalWidth = BAR_COUNT * (BAR_WIDTH + BAR_GAP);
    canvas.width = totalWidth;
    canvas.height = CANVAS_HEIGHT;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      phaseRef.current += 0.06;

      for (let i = 0; i < BAR_COUNT; i++) {
        const normalised = i / BAR_COUNT;
        const wave1 = Math.sin(phaseRef.current + normalised * Math.PI * 3) * 0.5 + 0.5;
        const wave2 = Math.sin(phaseRef.current * 1.5 + normalised * Math.PI * 5) * 0.3 + 0.3;
        const amplitude = isRecording ? (wave1 + wave2) * 0.5 : 0.1;
        const barHeight = Math.max(3, amplitude * CANVAS_HEIGHT * 0.85);
        const x = i * (BAR_WIDTH + BAR_GAP);
        const y = (CANVAS_HEIGHT - barHeight) / 2;

        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        gradient.addColorStop(0, '#818cf8');
        gradient.addColorStop(1, '#6366f1');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, BAR_WIDTH, barHeight, 1.5);
        ctx.fill();
      }

      frameRef.current = requestAnimationFrame(draw);
    };

    if (isRecording) {
      draw();
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < BAR_COUNT; i++) {
        const x = i * (BAR_WIDTH + BAR_GAP);
        const y = (CANVAS_HEIGHT - 3) / 2;
        ctx.fillStyle = '#2a2a3e';
        ctx.beginPath();
        ctx.roundRect(x, y, BAR_WIDTH, 3, 1.5);
        ctx.fill();
      }
    }

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [isRecording]);

  return (
    <div className="waveform-container">
      <canvas ref={canvasRef} className="waveform-canvas" />
      <div className="waveform-label">
        {isRecording && <span className="waveform-dot" />}
        {isRecording ? 'Listening...' : 'Ready to record'}
      </div>
    </div>
  );
}
