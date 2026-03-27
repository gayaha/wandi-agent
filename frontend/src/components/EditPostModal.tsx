import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { supabase } from '@/lib/supabase';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { useLanguage } from '@/contexts/LanguageContext';

interface Post {
  id: string;
  caption: string;
  media_url: string;
  scheduled_at: string;
  status: string;
}

interface EditPostModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  post: Post | null;
  onSuccess?: () => void;
}

export default function EditPostModal({ open, onOpenChange, post, onSuccess }: EditPostModalProps) {
  const { t } = useLanguage();
  const [caption, setCaption] = useState('');
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (post) {
      setCaption(post.caption || '');
      const dt = new Date(post.scheduled_at);
      setScheduleDate(format(dt, 'yyyy-MM-dd'));
      setScheduleTime(format(dt, 'HH:mm'));
    }
  }, [post]);

  const handleSave = async () => {
    if (!post) return;
    setSaving(true);

    const scheduledAt = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();

    const { error } = await supabase
      .from('scheduled_posts')
      .update({ caption, scheduled_at: scheduledAt })
      .eq('id', post.id);

    if (error) {
      toast.error(t('editPost.saveError'));
    } else {
      toast.success(t('editPost.saveSuccess'));
      onSuccess?.();
      onOpenChange(false);
    }
    setSaving(false);
  };

  if (!post) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass border-border bg-card sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">{t('editPost.title')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {post.media_url && (
            <img src={post.media_url} alt="Preview" className="w-full h-48 object-cover rounded-lg" />
          )}

          <div className="space-y-2">
            <Label>{t('editPost.caption')}</Label>
            <Textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              className="bg-secondary/50 border-border min-h-[100px] resize-none"
              maxLength={2200}
            />
            <p className="text-xs text-muted-foreground text-left" dir="ltr">
              {caption.length}/2200
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">{t('editPost.date')}</Label>
              <Input
                type="date"
                value={scheduleDate}
                onChange={(e) => setScheduleDate(e.target.value)}
                className="bg-secondary/50 border-border"
                dir="ltr"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t('editPost.time')}</Label>
              <Input
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                className="bg-secondary/50 border-border"
                dir="ltr"
              />
            </div>
          </div>

          <Button
            onClick={handleSave}
            disabled={saving}
            className="w-full gradient-primary text-primary-foreground font-semibold h-11"
          >
            {saving && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
            {t('editPost.saveChanges')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
