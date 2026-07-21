import { Component, ErrorInfo, ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';

interface ErrorBoundaryState {
  message: string | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { message: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App render failed', error, info);
  }

  handleRetry = () => {
    this.setState({ message: null });
  };

  render() {
    if (!this.state.message) return this.props.children;

    return (
      <main className="welcome-screen">
        <div className="welcome-logo" style={{ background: 'linear-gradient(135deg, #ef4444, #f97316)' }}>
          <span style={{ fontSize: 28 }}>!</span>
        </div>
        <h1 style={{ fontSize: '1.8rem' }}>Something went wrong</h1>
        <div className="alert" role="alert" style={{ maxWidth: 480, textAlign: 'left' }}>
          <strong>UI_ERROR</strong>
          <span>{this.state.message}</span>
        </div>
        <button
          className="btn-primary"
          onClick={this.handleRetry}
          style={{ marginTop: 20 }}
        >
          <RefreshCw size={18} aria-hidden />
          Try Again
        </button>
      </main>
    );
  }
}
