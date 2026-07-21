import { ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { API_URL, LanguageCode } from '../lib/config';

export interface TranscriptData {
  text: string;
  lang: string;
  avg_logprob: number;
  lowConfidence: boolean;
}

export interface TokenData {
  token: string;
  sessionId: string;
}

export interface SentenceData {
  sentence: string;
  index: number;
  sessionId: string;
}

export interface AudioData {
  audio: string;
  format: string;
  lang: string;
  index: number;
}

export interface ErrorData {
  code: string;
  message: string;
  retryable: boolean;
}

interface WebSocketHandlers {
  onTranscript?: (data: TranscriptData) => void;
  onToken?: (data: TokenData) => void;
  onSentence?: (data: SentenceData) => void;
  onAudio?: (data: AudioData) => void;
  onDone?: (data: { sessionId: string; totalTokens: number }) => void;
  onError?: (data: ErrorData) => void;
}

interface WebSocketContextType {
  connected: boolean;
  sessionId: string | null;
  language: LanguageCode;
  setLanguage: (language: LanguageCode) => void;
  initSession: (token: string) => void;
  submitQuery: (frame: string, audio: string) => void;
  endSession: () => void;
  setHandlers: (handlers: WebSocketHandlers) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children, url = API_URL }: { children: ReactNode; url?: string }) {
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [language, setLanguage] = useState<LanguageCode>('en');
  const socketRef = useRef<Socket | null>(null);
  const handlersRef = useRef<WebSocketHandlers>({});
  // Refs mirror the latest auth/session/language so the socket 'connect'
  // handler (bound once) can re-initialise the session on every reconnect.
  const tokenRef = useRef<string>('');
  const sessionIdRef = useRef<string | null>(null);
  const languageRef = useRef<LanguageCode>('en');

  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  const emitInit = useCallback(() => {
    if (!tokenRef.current) return;
    // Passing the existing sessionId lets the backend rebind and rehydrate the
    // conversation context instead of orphaning it after a reconnect (spec 5.6).
    socketRef.current?.emit('session:init', {
      language: languageRef.current,
      userId: 'web-demo',
      token: tokenRef.current,
      sessionId: sessionIdRef.current ?? undefined,
    });
  }, []);

  useEffect(() => {
    const socket = io(url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30000,
      randomizationFactor: 0.5,
    });

    socketRef.current = socket;
    socket.on('connect', () => {
      setConnected(true);
      // Re-establish the session automatically on connect and every reconnect.
      emitInit();
    });
    socket.on('disconnect', () => setConnected(false));
    socket.on('connect_error', () => setConnected(false));
    socket.on('session:init', (data: { sessionId: string }) => {
      sessionIdRef.current = data.sessionId;
      setSessionId(data.sessionId);
    });
    socket.on('transcript:ready', (data: TranscriptData) => handlersRef.current.onTranscript?.(data));
    socket.on('response:token', (data: TokenData) => handlersRef.current.onToken?.(data));
    socket.on('response:sentence', (data: SentenceData) => handlersRef.current.onSentence?.(data));
    socket.on('response:audio', (data: AudioData) => handlersRef.current.onAudio?.(data));
    socket.on('response:done', (data: { sessionId: string; totalTokens: number }) => handlersRef.current.onDone?.(data));
    socket.on('error:occurred', (data: ErrorData) => handlersRef.current.onError?.(data));

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [emitInit, url]);

  const setHandlers = useCallback((handlers: WebSocketHandlers) => {
    handlersRef.current = handlers;
  }, []);

  const initSession = useCallback((token: string) => {
    tokenRef.current = token;
    emitInit();
  }, [emitInit]);

  const submitQuery = useCallback((frame: string, audio: string) => {
    const activeSession = sessionIdRef.current;
    if (!activeSession) return;
    socketRef.current?.emit('query:submit', { frame, audio, sessionId: activeSession });
  }, []);

  const endSession = useCallback(() => {
    const activeSession = sessionIdRef.current;
    if (!activeSession) return;
    socketRef.current?.emit('session:end', { sessionId: activeSession });
    tokenRef.current = '';
    sessionIdRef.current = null;
    setSessionId(null);
  }, []);

  const value = useMemo<WebSocketContextType>(() => ({
    connected,
    sessionId,
    language,
    setLanguage,
    initSession,
    submitQuery,
    endSession,
    setHandlers,
  }), [connected, endSession, initSession, language, sessionId, setHandlers, submitQuery]);

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) throw new Error('useWebSocket must be used within WebSocketProvider');
  return context;
}
