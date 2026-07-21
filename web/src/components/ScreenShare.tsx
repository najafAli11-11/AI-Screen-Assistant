import { useCallback, useRef, useState } from 'react';

interface ScreenShareResult {
  startCapture: () => Promise<void>;
  stopCapture: () => void;
  captureFrame: () => Promise<string>;
  isCapturing: boolean;
  error: string | null;
}

export function useScreenShare(): ScreenShareResult {
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const stopCapture = useCallback(() => {
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
      videoRef.current = null;
    }
    setIsCapturing(false);
  }, []);

  const startCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 1 },
        audio: false,
      });
      const video = document.createElement('video');
      video.muted = true;
      video.playsInline = true;
      video.srcObject = stream;
      await video.play();
      if (!video.videoWidth) {
        await new Promise<void>(resolve => {
          video.onloadedmetadata = () => resolve();
        });
      }

      streamRef.current = stream;
      videoRef.current = video;
      stream.getVideoTracks()[0]?.addEventListener('ended', stopCapture);
      setIsCapturing(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screen capture failed');
      setIsCapturing(false);
    }
  }, [stopCapture]);

  const captureFrame = useCallback(async (): Promise<string> => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return '';

    // Wait for the browser to deliver the latest screen frame after a tab
    // switch.  Off-DOM video elements are throttled by Chromium-based browsers
    // when their owning tab loses focus; a short delay lets the stream catch up.
    await new Promise(resolve => setTimeout(resolve, 1000));

    const maxWidth = 1280;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext('2d');
    if (!context) return '';
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.7).split(',')[1] ?? '';
  }, []);

  return { startCapture, stopCapture, captureFrame, isCapturing, error };
}
