import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { publishPost } from '@/lib/edge-functions';
import { toast } from 'sonner';
import { sanitizeError } from '@/utils/sanitizeError';

interface PublishParams {
  connectionId: string;
  files: File[];
  caption: string;
  scheduleAt?: string;
  mediaType?: 'image' | 'video' | 'carousel';
}

export function usePublishPost() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const publish = async ({ connectionId, files, caption, scheduleAt, mediaType }: PublishParams) => {
    setLoading(true);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error('Not authenticated');

      const uploadedMedia: { url: string; path: string; type: 'image' | 'video' }[] = [];

      for (const file of files) {
        const ext = file.name.split('.').pop();
        const filePath = `${session.user.id}/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;

        const { error: uploadError } = await supabase.storage
          .from('post-media')
          .upload(filePath, file);

        if (uploadError) throw uploadError;

        const { data: urlData } = supabase.storage
          .from('post-media')
          .getPublicUrl(filePath);

        const isVideo = file.type.startsWith('video/');
        uploadedMedia.push({
          url: urlData.publicUrl,
          path: filePath,
          type: isVideo ? 'video' : 'image',
        });
      }

      const resolvedType = mediaType || (files.length > 1 ? 'carousel' : (files[0].type.startsWith('video/') ? 'video' : 'image'));

      const body: any = {
        connection_id: connectionId,
        caption,
        media_url: uploadedMedia[0].url,
        media_storage_path: uploadedMedia[0].path,
        media_type: resolvedType,
      };

      if (resolvedType === 'carousel') {
        body.carousel_items = uploadedMedia.map(m => ({
          media_url: m.url,
          media_storage_path: m.path,
          item_type: m.type,
        }));
      }

      if (scheduleAt) {
        body.schedule_at = scheduleAt;
      }

      const result = await publishPost(body);
      toast.success(result.scheduled ? 'הפוסט תוזמן בהצלחה!' : 'הפוסט פורסם בהצלחה!');
      return result;
    } catch (err: any) {
      const friendly = sanitizeError(err);
      setError(friendly);
      toast.error(friendly);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { publish, loading, error };
}
