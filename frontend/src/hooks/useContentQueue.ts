import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { getContentQueue } from '@/lib/edge-functions';

export interface ContentQueueItem {
  id: string;
  [key: string]: any;
}

export function useContentQueue() {
  const { session } = useAuth();
  const [items, setItems] = useState<ContentQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [debug, setDebug] = useState<any>(null);

  const fetchQueue = useCallback(async () => {
    if (!session?.access_token) {
      setItems([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const data = await getContentQueue();
      setItems(data.items || []);
      setDebug(data.debug || null);
    } catch (err) {
      if (import.meta.env.DEV) console.error('Content queue fetch error:', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  return { items, loading, refresh: fetchQueue, debug };
}
