import { useCallback, useEffect, useMemo, useState } from 'react';
import { Headphones, MonitorUp, Play, Power, Radio, ShieldCheck, Square, Volume2 } from 'lucide-react';
import { AudioWaveform } from './components/AudioWaveform';
import { CaptionOverlay } from './components/CaptionOverlay';
import { ChatHistory } from './components/ChatHistory';
import { FloatingAsk } from './components/FloatingAsk';
import { LoadingSpinner } from './components/LoadingSpinner';
import { PipelineProgress } from './components/PipelineProgress';
import { useAudioRecorder } from './components/AudioRecorder';
import { usePlaybackQueue } from './components/PlaybackQueue';
import { useScreenShare } from './components/ScreenShare';
import { WelcomeScreen } from './components/WelcomeScreen';
import { ErrorData, TranscriptData, WebSocketProvider, useWebSocket } from './hooks/useWebSocket';
import { requestToken } from './lib/api';
import { LANGUAGES, LanguageCode } from './lib/config';
import { readSessionValue, removeSessionValue, writeSessionValue } from './lib/storage';
import './styles/app.css';

type RunState = 'idle' | 'capturing' | 'recording' | 'processing';

function AppInner() {
  const {
    connected,
    sessionId,
    language,
    setLanguage,
    initSession,
    submitQuery,
    endSession,
    setHandlers,
  } = useWebSocket();
  const { startCapture, stopCapture, captureFrame, isCapturing, error: screenError } = useScreenShare();
  const { recordClip, isRecording, error: micError } = useAudioRecorder();
  const playback = usePlaybackQueue();

  const [accessCode, setAccessCode] = useState(() => readSessionValue('asa_access_code'));
  const [token, setToken] = useState(() => readSessionValue('asa_token'));
  const [runState, setRunState] = useState<RunState>('idle');
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [response, setResponse] = useState('');
  const [steps, setSteps] = useState<string[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  const [error, setError] = useState<ErrorData | null>(null);

  const addEvent = useCallback((message: string) => {
    setEvents(previous => [`${new Date().toLocaleTimeString()} ${message}`, ...previous].slice(0, 8));
  }, []);

  useEffect(() => {
    setHandlers({
      onTranscript: data => {
        setTranscript(data);
        addEvent(`Transcript ready (${data.lang}${data.lowConfidence ? ', low confidence' : ''})`);
      },
      onToken: data => setResponse(previous => previous + data.token),
      onSentence: data => {
        setSteps(previous => [...previous, data.sentence]);
        addEvent(`Step ${data.index + 1} received`);
      },
      onAudio: data => {
        playback.enqueue(data);
        addEvent(`Audio ${data.index + 1} queued`);
      },
      onDone: data => {
        setRunState('capturing');
        addEvent(`Response complete (${data.totalTokens} tokens)`);
      },
      onError: data => {
        setError(data);
        setRunState(isCapturing ? 'capturing' : 'idle');
        addEvent(`${data.code}: ${data.message}`);
        if (data.code === 'AUTH_001' && !data.retryable) {
          setToken('');
          removeSessionValue('asa_token');
        }
      },
    });
  }, [addEvent, isCapturing, playback, setHandlers]);

  useEffect(() => {
    if (token && connected && !sessionId) initSession(token);
  }, [connected, initSession, sessionId, token]);

  useEffect(() => {
    if (token && connected && sessionId) initSession(token);
  }, [language]); // eslint-disable-line react-hooks/exhaustive-deps

  const canAsk = connected && Boolean(sessionId) && isCapturing && runState !== 'processing' && runState !== 'recording';

  const statusText = useMemo(() => {
    if (!connected) return 'Backend disconnected';
    if (!sessionId) return 'Opening session';
    if (runState === 'recording') return 'Listening';
    if (runState === 'processing') return 'Thinking';
    if (isCapturing) return 'Ready';
    return 'Screen share off';
  }, [connected, isCapturing, runState, sessionId]);

  const pipelineStage = useMemo(() => {
    if (runState === 'recording') return 1;
    if (runState === 'processing' && !transcript) return 2;
    if (runState === 'processing' && transcript && steps.length === 0) return 3;
    if (runState === 'processing' && steps.length > 0) return 4;
    if (playback.isPlaying) return 5;
    if (runState === 'capturing' && steps.length > 0) return 5;
    return -1;
  }, [runState, transcript, steps.length, playback.isPlaying]);

  const handleAuthenticate = useCallback(async (code: string) => {
    setError(null);
    try {
      const result = await requestToken(code);
      writeSessionValue('asa_access_code', code);
      writeSessionValue('asa_token', result.token);
      setAccessCode(code);
      setToken(result.token);
      addEvent('Authenticated');
    } catch (err) {
      setError({ code: 'AUTH_001', message: err instanceof Error ? err.message : 'Authentication failed', retryable: true });
    }
  }, [addEvent]);

  const handleStart = useCallback(async () => {
    setError(null);
    try {
      if (!isCapturing) await startCapture();
      setRunState('capturing');
      initSession(token!);
      addEvent('Session started');
    } catch (err) {
      setError({ code: 'CAP_001', message: err instanceof Error ? err.message : 'Failed to start', retryable: true });
    }
  }, [addEvent, initSession, isCapturing, startCapture, token]);

  const handleAsk = useCallback(async () => {
    if (!canAsk) return;
    setRunState('recording');
    setError(null);
    setTranscript(null);
    setResponse('');
    setSteps([]);
    playback.clear();

    const frame = await captureFrame();
    if (!frame) {
      setError({ code: 'CAP_001', message: 'Screen frame is unavailable. Re-share your screen.', retryable: true });
      setRunState(isCapturing ? 'capturing' : 'idle');
      return;
    }

    addEvent('Recording question');
    const audio = await recordClip(7000);
    setRunState('processing');
    addEvent('Query submitted');
    submitQuery(frame, audio);
  }, [addEvent, canAsk, captureFrame, isCapturing, playback, recordClip, submitQuery]);

  const handleStop = useCallback(() => {
    playback.clear();
    stopCapture();
    endSession();
    setRunState('idle');
    setTranscript(null);
    setResponse('');
    setSteps([]);
    addEvent('Session stopped');
  }, [addEvent, endSession, playback, stopCapture]);

  // Show welcome screen if not authenticated
  if (!token) {
    return <WelcomeScreen onAuthenticate={handleAuthenticate} error={error?.message} />;
  }

  return (
    <main className="app-shell">
      <section className="control-panel">
        <div className="brand-row">
          <div>
            <p className="eyebrow">Realtime screen guidance</p>
            <h1>AI Screen Assistant</h1>
          </div>
          <span className={`status-pill ${connected ? 'online' : 'offline'}`}>
            <Radio size={14} aria-hidden />
            {statusText}
          </span>
        </div>

        <div className="setup-grid">
          <label>
            Guidance language
            <select value={language} onChange={event => setLanguage(event.target.value as LanguageCode)}>
              {LANGUAGES.map(item => (
                <option key={item.code} value={item.code}>{item.nativeName} - {item.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="action-row">
          <button className="btn-primary" onClick={handleStart} disabled={runState !== 'idle' && isCapturing}>
            <MonitorUp size={18} aria-hidden />
            {isCapturing ? 'Screen Shared' : 'Start Screen Share'}
          </button>
          <button className="btn-accent" onClick={handleAsk} disabled={!canAsk}>
            {isRecording ? <Square size={18} aria-hidden /> : <Play size={18} aria-hidden />}
            {runState === 'recording' ? 'Listening...' : runState === 'processing' ? 'Processing...' : 'Ask'}
          </button>
          <button className="btn-secondary" onClick={handleStop} disabled={runState === 'idle' && !isCapturing}>
            <Power size={18} aria-hidden />
            Stop
          </button>
          <FloatingAsk
            canAsk={canAsk}
            askLabel={runState === 'recording' ? 'Listening' : runState === 'processing' ? 'Processing' : 'Ask'}
            statusText={statusText}
            isListening={runState === 'recording'}
            onAsk={handleAsk}
          />
        </div>

        {(error || screenError || micError) && (
          <div className="alert" role="alert">
            <strong>{error?.code ?? 'CAPTURE'}</strong>
            <span>{error?.message ?? screenError ?? micError}</span>
          </div>
        )}
      </section>

      {pipelineStage >= 0 && <PipelineProgress activeStage={pipelineStage} />}

      {isRecording && <AudioWaveform isRecording={isRecording} />}

      {runState === 'processing' && !transcript && (
        <LoadingSpinner text="Analyzing your screen and question..." />
      )}

      <section className="workspace">
        <div className="result-column">
          <div className="metric-strip">
            <div>
              <ShieldCheck size={16} aria-hidden />
              <span>{sessionId ? 'Session secured' : 'No session'}</span>
            </div>
            <div>
              <Headphones size={16} aria-hidden />
              <span>{playback.isPlaying ? `Playing step ${(playback.currentIndex ?? 0) + 1}` : `${playback.queuedCount} audio queued`}</span>
            </div>
            <div>
              <Volume2 size={16} aria-hidden />
              <span>{steps.length} steps</span>
            </div>
          </div>

          {transcript && (
            <article className={`transcript ${transcript.lowConfidence ? 'warn' : ''}`}>
              <h2>Transcript</h2>
              <p>{transcript.text || 'No speech detected'}</p>
              <span>{transcript.lang.toUpperCase()} confidence {transcript.avg_logprob.toFixed(2)}</span>
            </article>
          )}

          <ChatHistory
            transcript={transcript}
            response={response}
            steps={steps}
            isPlaying={playback.isPlaying}
            currentAudioStep={playback.currentIndex}
            audioTotal={steps.length}
          />
        </div>

        <aside className="steps-panel">
          <h2>Steps</h2>
          {steps.length === 0 ? (
            <p className="muted" style={{ color: 'var(--text-faint)', fontSize: '0.88rem' }}>
              Generated steps will appear here and as captions.
            </p>
          ) : (
            <ol>
              {steps.map((step, index) => <li key={`${step}-${index}`}>{step}</li>)}
            </ol>
          )}
          <div className="event-log">
            <h3>Recent Events</h3>
            {events.map(event => <p key={event}>{event}</p>)}
          </div>
        </aside>
      </section>

      <CaptionOverlay texts={steps} active={steps.length > 0} />
    </main>
  );
}

export default function App() {
  return (
    <WebSocketProvider>
      <AppInner />
    </WebSocketProvider>
  );
}
