import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { getMagnets } from '@/lib/edge-functions';

export interface Magnet {
  id: string;
  name: string;
  client: string;
  description: string;
  awareness_stage: string;
  trigger_word: string;
  cta: string;
  full_prompt: string;
}

export function useMagnets() {
  const { session } = useAuth();
  const [magnets, setMagnets] = useState<Magnet[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchMagnets = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const data = await getMagnets();
      setMagnets(data.magnets || []);
    } catch (err) {
      if (import.meta.env.DEV) console.error('Error fetching magnets:', err);
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    fetchMagnets();
  }, [fetchMagnets]);

  return { magnets, loading, fetchMagnets };
}
