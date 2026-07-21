import { useCallback, useState } from 'react';

interface AudioRecorderResult {
  recordClip: (durationMs?: number) => Promise<string>;
  isRecording: boolean;
  error: string | null;
}

export function useAudioRecorder(): AudioRecorderResult {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recordClip = useCallback(async (durationMs = 5000): Promise<string> => {
    setIsRecording(true);
    setError(null);
    let stream: MediaStream | null = null;
    let audioContext: AudioContext | null = null;

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } });
      audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      const samples: Float32Array[] = [];

      processor.onaudioprocess = event => {
        samples.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      await new Promise(resolve => window.setTimeout(resolve, durationMs));
      processor.disconnect();
      source.disconnect();

      const wav = encodeWav(samples, audioContext.sampleRate);
      return await blobToBase64(new Blob([wav], { type: 'audio/wav' }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Microphone capture failed');
      return '';
    } finally {
      stream?.getTracks().forEach(track => track.stop());
      await audioContext?.close().catch(() => undefined);
      setIsRecording(false);
    }
  }, []);

  return { recordClip, isRecording, error };
}

function encodeWav(chunks: Float32Array[], sampleRate: number): ArrayBuffer {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, sampleCount * 2, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
      offset += 2;
    }
  }
  return buffer;
}

function writeString(view: DataView, offset: number, value: string) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onloadend = () => resolve(String(reader.result).split(',')[1] ?? '');
    reader.readAsDataURL(blob);
  });
}
