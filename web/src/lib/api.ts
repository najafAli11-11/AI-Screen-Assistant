import { API_URL } from './config';

interface TokenResponse {
  token: string;
  expiresInSeconds: number;
}

export async function requestToken(secret: string): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/api/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ secret }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Unable to authenticate' }));
    throw new Error(body.detail ?? 'Unable to authenticate');
  }

  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${API_URL}/api/health`);
  if (!response.ok) throw new Error('Backend health check failed');
  return response.json();
}
