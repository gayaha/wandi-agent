import { supabase } from './supabase';

const AGENT_BASE_URL = import.meta.env.VITE_AGENT_API_URL || 'https://agent.gayafinkhaelyon.online';

if (import.meta.env.DEV && !import.meta.env.VITE_AGENT_API_URL) {
  console.warn('VITE_AGENT_API_URL not set in .env — using fallback');
}

async function getAccessToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function agentFetch(path: string, options: RequestInit = {}) {
  const token = await getAccessToken();
  if (!token) throw new Error('Not authenticated');
  const res = await fetch(`${AGENT_BASE_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

// Chat endpoints
export async function sendChatMessage(message: string, sessionId?: string) {
  return agentFetch('/agent/chat?async=true', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export async function getChatSessions() {
  return agentFetch('/agent/sessions');
}

export async function getSessionMessages(sessionId: string) {
  return agentFetch(`/agent/sessions/${sessionId}/messages`);
}

export async function pollSession(sessionId: string, signal?: AbortSignal) {
  return agentFetch(`/agent/sessions/${sessionId}/poll`, { signal });
}

export async function getQuota() {
  return agentFetch('/agent/quota');
}
