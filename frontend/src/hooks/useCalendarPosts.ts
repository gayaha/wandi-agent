import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';

interface ScheduledPost {
  id: string;
  caption: string;
  media_url: string;
  scheduled_at: string;
  status: string;
  [key: string]: any;
}

export function useCalendarPosts(year: number, month: number, connectionId?: string) {
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    const startOfMonth = new Date(year, month, 1).toISOString();
    const endOfMonth = new Date(year, month + 1, 0, 23, 59, 59).toISOString();

    let query = supabase
      .from('scheduled_posts')
      .select('*')
      .gte('scheduled_at', startOfMonth)
      .lte('scheduled_at', endOfMonth)
      .order('scheduled_at', { ascending: true });

    if (connectionId) {
      query = query.eq('meta_connection_id', connectionId);
    }

    const { data, error } = await query;

    if (!error && data) {
      setPosts(data);
    }
    setLoading(false);
  }, [year, month]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  const postsByDate: Record<string, ScheduledPost[]> = {};
  posts.forEach((post) => {
    const day = new Date(post.scheduled_at).toISOString().split('T')[0];
    if (!postsByDate[day]) postsByDate[day] = [];
    postsByDate[day].push(post);
  });

  return { posts, postsByDate, loading, refetch: fetchPosts };
}
