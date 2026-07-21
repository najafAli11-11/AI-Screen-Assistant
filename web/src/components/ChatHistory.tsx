import { useEffect, useRef } from 'react';
import { Mic, Volume2 } from 'lucide-react';
import { TranscriptData } from '../hooks/useWebSocket';

interface ChatEntry {
  type: 'user' | 'ai';
  text: string;
  lang?: string;
  audioStep?: number;
  audioTotal?: number;
}

interface ChatHistoryProps {
  transcript: TranscriptData | null;
  response: string;
  steps: string[];
  isPlaying: boolean;
  currentAudioStep: number | null;
  audioTotal: number;
}

export function ChatHistory({
  transcript,
  response,
  steps,
  isPlaying,
  currentAudioStep,
  audioTotal,
}: ChatHistoryProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasContent = transcript || response;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, response, steps.length]);

  const messages: ChatEntry[] = [];

  if (transcript) {
    messages.push({
      type: 'user',
      text: transcript.text || '(No speech detected)',
      lang: transcript.lang,
    });
  }

  if (response) {
    messages.push({
      type: 'ai',
      text: response,
      audioStep: isPlaying && currentAudioStep !== null ? currentAudioStep : undefined,
      audioTotal: audioTotal || undefined,
    });
  }

  return (
    <article className="response-pane">
      <h2>Conversation</h2>
      {!hasContent ? (
        <div className="chat-empty">
          Start a session, share your screen, then ask a question aloud.
        </div>
      ) : (
        <div className="chat-history" ref={scrollRef}>
          {messages.map((msg, index) => (
            <div key={index} className="chat-message">
              <div className={`chat-avatar ${msg.type}`}>
                {msg.type === 'user' ? <Mic size={16} /> : 'AI'}
              </div>
              <div className="chat-bubble">
                <div className="chat-bubble-label">
                  {msg.type === 'user' ? 'You' : 'AI Assistant'}
                  {msg.lang && <span className="lang-tag">{msg.lang.toUpperCase()}</span>}
                </div>
                <div className="chat-bubble-text">{msg.text}</div>
                {msg.audioStep !== undefined && msg.audioTotal !== undefined && (
                  <div className="chat-bubble-audio">
                    <Volume2 size={14} />
                    Playing step {msg.audioStep + 1} / {msg.audioTotal}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
