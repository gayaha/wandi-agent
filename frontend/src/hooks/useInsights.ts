import { useState, useEffect } from 'react';
import { getInsights } from '@/lib/edge-functions';

interface DailyStat {
  date: string;
  reach: number;
  impressions: number;
}

interface TopPost {
  id: string;
  caption: string;
  media_url: string;
  thumbnail_url?: string;
  media_type: string;
  likes: number;
  comments: number;
  reach: number;
  timestamp: string;
}

export interface Insights {
  reach: number;
  impressions: number;
  follower_count: number;
  engagement_rate: number;
  daily_stats: DailyStat[];
  top_posts: TopPost[];
}

export function useInsights(connectionId: string | undefined) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!connectionId) return;

    const fetchInsights = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getInsights(connectionId);
        setInsights(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, [connectionId]);

  return { insights, loading, error };
}
