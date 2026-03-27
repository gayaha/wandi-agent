import { useState, useEffect, useCallback, useRef } from 'react';
import { agentFetch } from '@/lib/api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tools_used?: string[];
  total_duration_ms?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  status: string;
}

export interface Quota {
  allowed: boolean;
  plan: string;
  messages: { used: number; limit: number; remaining: number };
  reset_time: string;
}

const POLL_INTERVAL_MS = 5000;
const POLL_MAX_ATTEMPTS = 120;
const THINKING_PLACEHOLDER = '\u23F3 וונדי עובדת על הבקשה שלך...';

interface PollResult {
  status: 'complete' | 'error' | 'processing';
  response?: string;
  session_id?: string;
  tools_used?: string[];
  total_duration_ms?: number;
}

async function pollForResult(sessionId: string, signal: AbortSignal): Promise<PollResult> {
  for (let i = 0; i < POLL_MAX_ATTEMPTS; i++) {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, POLL_INTERVAL_MS);
      signal.addEventListener('abort', () => {
        clearTimeout(timer);
        reject(new DOMException('Polling aborted', 'AbortError'));
      }, { once: true });
    });

    const data: PollResult = await agentFetch(
      `/agent/sessions/${sessionId}/poll`,
      { signal },
    );

    if (data.status === 'complete' || data.status === 'error') {
      return data;
    }
  }

  return { status: 'error', response: 'הבקשה לקחה יותר מדי זמן. נסי שוב.' };
}

export function useAgentChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [sending, setSending] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchQuota = useCallback(async () => {
    try {
      const data = await agentFetch('/agent/quota');
      setQuota(data);
    } catch {}
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      setSessionsLoading(true);
      const data = await agentFetch('/agent/sessions');
      setSessions(data.sessions || []);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuota();
    fetchSessions();
  }, [fetchQuota, fetchSessions]);

  const selectSession = useCallback(async (sessionId: string) => {
    setActiveSessionId(sessionId);
    setMessages([]);
    setMessagesLoading(true);
    setError(null);
    try {
      const data = await agentFetch(`/agent/sessions/${sessionId}/messages`);
      setMessages((data.messages || []).filter((m: any) => m.role === 'user' || m.role === 'assistant'));
    } catch {
      setError('Failed to load messages');
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  const startNewChat = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setError(null);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || sending) return;
    setError(null);
    setSending(true);
    setElapsedSeconds(0);
    timerRef.current = setInterval(() => setElapsedSeconds(s => s + 10), 10000);

    const userMessage: ChatMessage = {
      role: 'user',
      content: text.trim(),
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    const thinkingMessage: ChatMessage = {
      role: 'assistant',
      content: THINKING_PLACEHOLDER,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, thinkingMessage]);

    try {
      abortRef.current = new AbortController();
      const { signal } = abortRef.current;

      const initData = await agentFetch('/agent/chat?async=true', {
        method: 'POST',
        body: JSON.stringify({
          message: text.trim(),
          session_id: activeSessionId || undefined,
        }),
        signal,
      });

      const sessionId = initData.session_id || activeSessionId;
      if (!activeSessionId && sessionId) {
        setActiveSessionId(sessionId);
      }

      let result: PollResult;
      if (initData.status === 'processing' && sessionId) {
        result = await pollForResult(sessionId, signal);
      } else {
        result = initData as PollResult;
      }

      if (result.status === 'error') {
        setMessages(prev => prev.filter(m => m.content !== THINKING_PLACEHOLDER));
        setError(result.response || 'שגיאה בעיבוד הבקשה. נסי שוב.');
      } else {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: result.response || '',
          created_at: new Date().toISOString(),
          tools_used: result.tools_used,
          total_duration_ms: result.total_duration_ms,
        };
        setMessages(prev =>
          prev.map(m => m.content === THINKING_PLACEHOLDER ? assistantMessage : m),
        );
      }

      fetchQuota();
      fetchSessions();
    } catch (err: any) {
      setMessages(prev => prev.filter(m => m.content !== THINKING_PLACEHOLDER));
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to send message');
      }
    } finally {
      setSending(false);
      setElapsedSeconds(0);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      abortRef.current = null;
    }
  }, [sending, activeSessionId, fetchQuota, fetchSessions]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return {
    sessions, sessionsLoading, activeSessionId, messages, messagesLoading,
    quota, sending, elapsedSeconds, error,
    selectSession, startNewChat, sendMessage, refreshSessions: fetchSessions,
  };
}
