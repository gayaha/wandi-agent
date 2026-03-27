import { supabase, SUPABASE_URL } from './supabase';

async function getToken(): Promise<string> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error('Not authenticated');
  return session.access_token;
}

async function edgeFetch(functionName: string, options: { method?: string; body?: any; params?: Record<string, string> } = {}) {
  const token = await getToken();
  const { method = 'GET', body, params } = options;

  let url = `${SUPABASE_URL}/functions/v1/${functionName}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    url += `?${qs}`;
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.error || `Edge function error: ${res.status}`);
  }

  return res.json();
}

export async function metaOAuthCallback(code: string, redirectUri: string) {
  return edgeFetch('meta-oauth-callback', {
    method: 'POST',
    body: { code, redirect_uri: redirectUri },
  });
}

export async function publishPost(payload: {
  connection_id: string;
  caption: string;
  media_url: string;
  media_storage_path?: string;
  media_type?: string;
  schedule_at?: string;
  carousel_items?: any[];
}) {
  return edgeFetch('publish-post', {
    method: 'POST',
    body: payload,
  });
}

export async function getMagnets() {
  return edgeFetch('get-magnets');
}

export async function getInsights(connectionId: string) {
  return edgeFetch('get-insights', {
    params: { connection_id: connectionId },
  });
}

export async function getPosts(connectionId: string, limit = 50, status?: string) {
  const params: Record<string, string> = { connection_id: connectionId, limit: String(limit) };
  if (status) params.status = status;
  return edgeFetch('get-posts', { params });
}

export async function getContentQueue() {
  return edgeFetch('get-content-queue');
}

export async function generateContent(payload: {
  connection_id: string;
  mode: string;
  quantity: number;
  manual_params?: any;
}) {
  return edgeFetch('generate-content', {
    method: 'POST',
    body: payload,
  });
}
