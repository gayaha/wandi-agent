import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';

const META_APP_ID = import.meta.env.VITE_META_APP_ID || '1610928366995658';

if (import.meta.env.DEV && !import.meta.env.VITE_META_APP_ID) {
  console.warn('VITE_META_APP_ID not set in .env — using fallback');
}

interface MetaConnection {
  id: string;
  user_id: string;
  page_id: string;
  page_name: string;
  ig_account_id: string;
  ig_username: string;
  meta_user_id: string;
  token_expires_at: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export function useMetaConnection() {
  const [connection, setConnection] = useState<MetaConnection | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchConnection = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('meta_connections')
      .select('id,user_id,page_id,page_name,ig_account_id,ig_username,meta_user_id,token_expires_at,status,created_at,updated_at')
      .eq('status', 'active')
      .maybeSingle();

    if (error && import.meta.env.DEV) {
      console.error('Error fetching connection:', error);
    }
    setConnection(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchConnection();
  }, [fetchConnection]);

  const connectInstagram = useCallback(() => {
    const redirectUri = `${window.location.origin}/auth/meta/callback`;
    const scopes = 'instagram_basic,instagram_content_publish,instagram_manage_insights,pages_show_list,pages_read_engagement';
    window.location.href = `https://www.facebook.com/v21.0/dialog/oauth?client_id=${META_APP_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${scopes}&response_type=code`;
  }, []);

  const disconnect = useCallback(async () => {
    if (!connection) return;
    const { error } = await supabase
      .from('meta_connections')
      .update({ status: 'disconnected' })
      .eq('id', connection.id);

    if (error) {
      toast.error('שגיאה בניתוק החשבון');
    } else {
      toast.success('החשבון נותק בהצלחה');
      setConnection(null);
    }
  }, [connection]);

  return { connection, loading, connectInstagram, disconnect, refetch: fetchConnection };
}
