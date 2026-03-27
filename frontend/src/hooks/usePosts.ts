import { useState, useEffect, useCallback } from 'react';
import { getPosts } from '@/lib/edge-functions';

interface ScheduledPost {
  id: string;
  caption: string;
  media_url: string;
  scheduled_at: string;
  status: string;
  meta_connection_id: string;
  error_message?: string;
  [key: string]: any;
}

export function usePosts(connectionId: string | undefined, status?: string) {
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPosts = useCallback(async () => {
    if (!connectionId) return;
    setLoading(true);
    try {
      const data = await getPosts(connectionId, 50, status);
      setPosts(data.posts || []);
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  }, [connectionId, status]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  return { posts, loading, refetch: fetchPosts };
}
