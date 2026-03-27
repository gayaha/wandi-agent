import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase, SUPABASE_URL } from '@/lib/supabase';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

const MetaCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [processing, setProcessing] = useState(true);
  const { t } = useLanguage();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      if (!code) {
        toast.error(t('metaCallback.noCode'));
        navigate('/settings');
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error(t('metaCallback.loginFirst'));
        navigate('/login');
        return;
      }

      try {
        const res = await fetch(`${SUPABASE_URL}/functions/v1/meta-oauth-callback`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code,
            redirect_uri: `${window.location.origin}/auth/meta/callback`,
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || 'Failed to connect');
        }

        const data = await res.json();
        toast.success(t('metaCallback.success').replace('{username}', data.ig_username));
      } catch (err: any) {
        toast.error(err.message || t('metaCallback.error'));
      }

      navigate('/');
    };

    handleCallback();
  }, [searchParams, navigate, t]);

  return (
    <div className="min-h-screen flex items-center justify-center gradient-bg">
      <div className="absolute inset-0 bg-background" />
      <div className="absolute inset-0 gradient-bg" />
      <div className="relative z-10 text-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
        <p className="text-lg text-muted-foreground">{t('metaCallback.connecting')}</p>
      </div>
    </div>
  );
};

export default MetaCallback;
