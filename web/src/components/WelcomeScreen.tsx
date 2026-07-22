import { useState } from 'react';
import { Eye, Mic, Globe, ArrowRight } from 'lucide-react';

interface WelcomeScreenProps {
  onAuthenticate: (code: string) => void;
  error?: string;
}

export function WelcomeScreen({ onAuthenticate, error }: WelcomeScreenProps) {
  const [code, setCode] = useState('');

  const handleSubmit = () => {
    if (code.trim()) onAuthenticate(code.trim());
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-logo">
        <Eye size={32} />
      </div>

      <h1 className="welcome-title">AI Screen Assistant</h1>
      <p className="welcome-subtitle">
        Share your screen, ask a question in your voice, and get instant
        step-by-step guidance — in Urdu, English, or Hindi.
      </p>

      <div className="welcome-features">
        <div className="feature-card">
          <div className="feature-icon purple">
            <Eye size={22} />
          </div>
          <h3>Screen Vision</h3>
          <p>See and understand what's on your screen using Claude Vision AI</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon orange">
            <Mic size={22} />
          </div>
          <h3>Voice Questions</h3>
          <p>Ask questions naturally — just speak and the AI listens</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon green">
            <Globe size={22} />
          </div>
          <h3>Multilingual</h3>
          <p>Get responses in Urdu, English, or Hindi with spoken audio</p>
        </div>
      </div>

      <div className="welcome-form">
        <input
          type="password"
          value={code}
          onChange={event => setCode(event.target.value)}
          onKeyDown={event => event.key === 'Enter' && handleSubmit()}
          placeholder="Enter access code"
          autoComplete="off"
        />
        <button className="btn-primary" onClick={handleSubmit} disabled={!code.trim()}>
          Get Started
          <ArrowRight size={18} aria-hidden />
        </button>
      </div>

      <p className="welcome-hint">
        Don&apos;t have an access code?{' '}
        <a
          href="https://github.com/najafAli11-11/AI-Screen-Assistant"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open the GitHub repo
        </a>{' '}
        to get it.
      </p>

      {error && (
        <div className="alert" role="alert" style={{ maxWidth: 440, marginTop: 16 }}>
          <strong>Auth Error</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="welcome-langs">
        <span className="lang-badge">Urdu</span>
        <span className="lang-badge">English</span>
        <span className="lang-badge">Hindi</span>
      </div>
    </div>
  );
}
