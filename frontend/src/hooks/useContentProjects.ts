import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

export interface TextOverlay {
  id: string;
  content: string;
  x: number;
  y: number;
  fontSize: number;
  color: string;
  fontWeight: string;
}

export interface OverlayConfig {
  texts: TextOverlay[];
}

export interface ContentProject {
  id: string;
  title: string | null;
  caption: string | null;
  video_text: string | null;
  source_video_url: string | null;
  source_video_path: string | null;
  processed_video_url: string | null;
  processed_video_path: string | null;
  overlay_config: OverlayConfig;
  status: string | null;
  created_at: string | null;
  updated_at: string | null;
  meta_connection_id: string | null;
  hook: string | null;
  hook_type: string | null;
  verbal_script: string | null;
  format: string | null;
  awareness_stage: string | null;
  magnet_name: string | null;
  airtable_record_id: string | null;
  batch_id: string | null;
  content_goal: string | null;
  client_name: string | null;
  rejection_notes: string | null;
}

export function useContentProjects() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<ContentProject[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchProjects = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('content_projects')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (error) throw error;

      setProjects((data || []).map(p => ({
        ...p,
        overlay_config: (p.overlay_config as any) || { texts: [] },
      })));
    } catch (err: any) {
      toast.error('שגיאה בטעינת פרויקטים');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const updateProject = useCallback(async (
    id: string,
    updates: {
      overlay_config?: OverlayConfig;
      status?: string;
      caption?: string;
      title?: string;
      verbal_script?: string;
      hook?: string;
      rejection_notes?: string;
    }
  ) => {
    try {
      const { error } = await supabase
        .from('content_projects')
        .update(updates as any)
        .eq('id', id);

      if (error) throw error;
      await fetchProjects();
    } catch (err: any) {
      toast.error('שגיאה בעדכון פרויקט');
    }
  }, [fetchProjects]);

  const deleteProject = useCallback(async (id: string) => {
    try {
      const { error } = await supabase
        .from('content_projects')
        .delete()
        .eq('id', id);

      if (error) throw error;
      toast.success('הפרויקט נמחק');
      await fetchProjects();
    } catch (err: any) {
      toast.error('שגיאה במחיקת פרויקט');
    }
  }, [fetchProjects]);

  const rejectProject = useCallback(async (id: string, notes: string) => {
    try {
      const { error } = await supabase
        .from('content_projects')
        .update({ status: 'rejected', rejection_notes: notes } as any)
        .eq('id', id);

      if (error) throw error;
      toast.success('הפרויקט נדחה');
      await fetchProjects();
    } catch (err: any) {
      toast.error('שגיאה בדחיית פרויקט');
    }
  }, [fetchProjects]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return { projects, loading, fetchProjects, updateProject, deleteProject, rejectProject };
}
