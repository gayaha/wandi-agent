import { useState } from 'react';
import AppLayout from '@/components/AppLayout';
import CreatePostModal from '@/components/CreatePostModal';
import EditPostModal from '@/components/EditPostModal';
import { useMetaConnection } from '@/hooks/useMetaConnection';
import { usePosts } from '@/hooks/usePosts';
import { supabase } from '@/lib/supabase';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Loader2, Trash2, Pencil, Clock, CheckCircle, XCircle, FileText, Image as ImageIcon } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/contexts/LanguageContext';

const PostsPage = () => {
  const { t } = useLanguage();
  const { connection } = useMetaConnection();
  const [activeTab, setActiveTab] = useState('pending');
  const { posts, loading, refetch } = usePosts(connection?.id, activeTab);
  const [createPostOpen, setCreatePostOpen] = useState(false);
  const [editingPost, setEditingPost] = useState<any>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const statusConfig: Record<string, { label: string; class: string }> = {
    pending: { label: t('posts.statusScheduled'), class: 'bg-primary/20 text-primary' },
    published: { label: t('posts.statusPublished'), class: 'bg-success/20 text-success' },
    draft: { label: t('posts.statusDraft'), class: 'bg-muted text-muted-foreground' },
    failed: { label: t('posts.statusFailed'), class: 'bg-destructive/20 text-destructive' },
    publishing: { label: t('posts.statusPublishing'), class: 'bg-warning/20 text-warning' },
  };

  const tabs = [
    { value: 'pending', label: t('posts.scheduled') },
    { value: 'published', label: t('posts.publishedTab') },
    { value: 'draft', label: t('posts.drafts') },
    { value: 'failed', label: t('posts.failedTab') },
  ];

  const handleDelete = async (id: string) => {
    setDeleting(id);
    const { error } = await supabase.from('scheduled_posts').delete().eq('id', id);
    if (error) {
      toast.error(t('posts.deleteError'));
    } else {
      toast.success(t('posts.deleteSuccess'));
      refetch();
    }
    setDeleting(null);
  };

  return (
    <AppLayout title={t('posts.title')} onNewPost={connection ? () => setCreatePostOpen(true) : undefined}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-secondary/50 border border-border">
          {tabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value} className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={activeTab}>
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : posts.length === 0 ? (
            <div className="glass p-12 text-center space-y-3">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto" />
              <p className="text-muted-foreground">{t('posts.noPostsInCategory')}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {posts.map((post) => (
                <div key={post.id} className="glass-hover overflow-hidden animate-fade-up">
                  {post.media_url ? (
                    <img src={post.media_url} className="w-full h-48 object-cover" alt="" />
                  ) : (
                    <div className="w-full h-48 bg-secondary/50 flex items-center justify-center">
                      <ImageIcon className="h-12 w-12 text-muted-foreground/30" />
                    </div>
                  )}
                  <div className="p-4 space-y-3">
                    <p className="text-sm line-clamp-2 min-h-[2.5rem]">{post.caption || t('dashboard.noCaption')}</p>
                    <div className="flex items-center justify-between">
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusConfig[post.status]?.class || '')}>
                        {statusConfig[post.status]?.label || post.status}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(post.scheduled_at), 'dd/MM/yy HH:mm')}
                      </span>
                    </div>
                    {post.error_message && (
                      <p className="text-xs text-destructive truncate">{post.error_message}</p>
                    )}
                    <div className="flex justify-end gap-1">
                      {post.status === 'pending' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingPost(post)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(post.id)}
                        disabled={deleting === post.id}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        {deleting === post.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {connection && (
        <CreatePostModal
          open={createPostOpen}
          onOpenChange={setCreatePostOpen}
          connectionId={connection.id}
          onSuccess={refetch}
        />
      )}

      <EditPostModal
        open={!!editingPost}
        onOpenChange={(v) => { if (!v) setEditingPost(null); }}
        post={editingPost}
        onSuccess={refetch}
      />
    </AppLayout>
  );
};

export default PostsPage;
