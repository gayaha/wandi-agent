import { useState } from 'react';
import AppLayout from '@/components/AppLayout';
import { useMetaConnection } from '@/hooks/useMetaConnection';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Instagram, LogOut, CheckCircle, XCircle, Calendar } from 'lucide-react';
import { format } from 'date-fns';

const SettingsPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useLanguage();
  const { connection, loading, connectInstagram, disconnect } = useMetaConnection();
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };

  return (
    <AppLayout title={t('settings.title')}>
      <div className="max-w-2xl space-y-6">
        {/* Instagram connection */}
        <div className="glass p-6 space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Instagram className="h-5 w-5 text-primary" />
            {t('settings.instagramConnection')}
          </h3>

          {loading ? (
            <div className="h-16 bg-secondary/30 animate-pulse rounded-lg" />
          ) : connection ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">@{connection.ig_username}</p>
                    <Badge variant="outline" className="bg-success/20 text-success border-success/30 text-xs">
                      <CheckCircle className="h-3 w-3 ml-1" />
                      {t('settings.active')}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{connection.page_name}</p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {t('settings.validUntil')} {format(new Date(connection.token_expires_at), 'dd/MM/yyyy')}
                  </p>
                </div>
              </div>
              <Button variant="outline" onClick={() => setDisconnectDialogOpen(true)} className="border-destructive/30 text-destructive hover:bg-destructive/10">
                <XCircle className="h-4 w-4 ml-2" />
                {t('settings.disconnectAccount')}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{t('settings.noAccountConnected')}</p>
              <Button onClick={connectInstagram} className="gradient-primary text-primary-foreground">
                <Instagram className="h-4 w-4 ml-2" />
                {t('settings.connectInstagram')}
              </Button>
            </div>
          )}
        </div>

        {/* Account */}
        <div className="glass p-6 space-y-4">
          <h3 className="text-lg font-semibold">{t('settings.account')}</h3>
          <div className="p-4 rounded-lg bg-secondary/30">
            <p className="text-sm text-muted-foreground">{t('settings.email')}</p>
            <p className="font-medium">{user?.email}</p>
          </div>
          <Button variant="outline" onClick={handleSignOut} className="border-border">
            <LogOut className="h-4 w-4 ml-2" />
            {t('settings.signOut')}
          </Button>
        </div>
      </div>

      <AlertDialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
        <AlertDialogContent className="glass border-border bg-card">
          <AlertDialogHeader>
            <AlertDialogTitle>{t('settings.disconnectTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('settings.disconnectDesc1')}
              {t('settings.disconnectDesc2')}
              {t('settings.disconnectDesc3')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-row-reverse gap-2">
            <AlertDialogCancel className="border-border">{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => { disconnect(); setDisconnectDialogOpen(false); }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('settings.disconnectAccount')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppLayout>
  );
};

export default SettingsPage;
