import { useState, useMemo } from 'react';
import AppLayout from '@/components/AppLayout';
import { useContentProjects, ContentProject } from '@/hooks/useContentProjects';
import { useContentQueue } from '@/hooks/useContentQueue';
import { useMetaConnection } from '@/hooks/useMetaConnection';
import { useRawMedia } from '@/hooks/useRawMedia';
import { useAuth } from '@/hooks/useAuth';
import { useMagnets } from '@/hooks/useMagnets';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Loader2,
  Film,
  RefreshCw,
  Sparkles,
  Wand2,
  SlidersHorizontal,
  Check,
  X,
  Undo2,
} from 'lucide-react';
import { SUPABASE_URL } from '@/lib/supabase';
import { toast } from 'sonner';
import { useLanguage } from '@/contexts/LanguageContext';

type GenerationMode = 'automatic' | 'manual';

interface ManualParams {
  topic?: string;
  magnet_id?: string;
  magnet_name?: string;
  content_type?: string;
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: 'content.statusDraft', color: 'bg-muted text-muted-foreground' },
  approved: { label: 'content.statusApproved', color: 'bg-green-500/20 text-green-400' },
  rejected: { label: 'content.statusRejected', color: 'bg-destructive/20 text-destructive' },
  scheduled: { label: 'content.statusScheduled', color: 'bg-primary/20 text-primary' },
};

export default function ContentPage() {
  const { projects, loading, fetchProjects, updateProject, rejectProject } = useContentProjects();
  const { items: airtableItems, loading: airtableLoading, refresh: refreshAirtable } = useContentQueue();
  const { connection } = useMetaConnection();
  const { session } = useAuth();
  const { folders: mediaFolders } = useRawMedia();
  const { magnets, loading: magnetsLoading } = useMagnets();
  const { t } = useLanguage();
  const hasVideos = mediaFolders.some(f => f.fileCount > 0);

  const [generating, setGenerating] = useState(false);
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [mode, setMode] = useState<GenerationMode>('automatic');
  const [manualParams, setManualParams] = useState<ManualParams>({});
  const [quantity, setQuantity] = useState(7);

  // Reject dialog state
  const [rejectingProject, setRejectingProject] = useState<ContentProject | null>(null);
  const [rejectionNotes, setRejectionNotes] = useState('');

  // Build Airtable maps for resilient fallback matching
  const airtableVideoMaps = useMemo(() => {
    const byRecordId: Record<string, string> = {};
    const byTitle: Record<string, string> = {};

    const normalize = (value?: string | null) =>
      (value || '').toLowerCase().replace(/\s+/g, ' ').trim();

    for (const item of airtableItems) {
      const videoField = item['Final Video'];
      const url = Array.isArray(videoField) ? videoField[0]?.url || '' : videoField || '';
      if (!url) continue;

      if (item.id) {
        byRecordId[item.id] = url;
      }

      const candidateTitles = [item['text on video'], item['ID'], item['Title']]
        .filter(Boolean)
        .map((v) => normalize(String(v)));

      for (const titleKey of candidateTitles) {
        if (titleKey) byTitle[titleKey] = url;
      }
    }

    return { byRecordId, byTitle };
  }, [airtableItems]);

  const handleGenerate = async () => {
    if (!connection || !session) {
      toast.error(t('content.connectError'));
      return;
    }

    setGenerating(true);
    setShowGenerateDialog(false);
    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/generate-content`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          connection_id: connection.id,
          mode,
          quantity,
          manual_params: mode === 'manual' ? manualParams : undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || t('content.createError'));
      }

      const result = await res.json();
      toast.success(
        t('content.createSuccess').replace('{count}', String(result.quantity || quantity))
      );
      setManualParams({});

      const pollIntervals = [5000, 15000, 30000, 60000, 120000];
      pollIntervals.forEach(delay => {
        setTimeout(() => { fetchProjects(); refreshAirtable(); }, delay);
      });
    } catch (err: any) {
      toast.error(err.message || t('content.createError'));
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async (project: ContentProject) => {
    await updateProject(project.id, { status: 'approved' });
    toast.success(t('content.projectApproved'));
  };

  const handleReject = async () => {
    if (!rejectingProject) return;
    await rejectProject(rejectingProject.id, rejectionNotes);
    setRejectingProject(null);
    setRejectionNotes('');
  };

  const handleReturnToDraft = async (project: ContentProject) => {
    await updateProject(project.id, { status: 'draft', rejection_notes: '' });
    toast.success(t('content.returnedToDraft'));
  };

  // Show draft projects first, then others
  const sortedProjects = [...projects].sort((a, b) => {
    const order = { draft: 0, rejected: 1, approved: 2, scheduled: 3 };
    return (order[a.status || 'draft'] ?? 4) - (order[b.status || 'draft'] ?? 4);
  });
  // Get video URL: prefer Supabase, fallback to Airtable by record id and title
  const getVideoUrl = (p: ContentProject) => {
    if (p.processed_video_url) return p.processed_video_url;
    if (p.source_video_url) return p.source_video_url;

    if (p.airtable_record_id && airtableVideoMaps.byRecordId[p.airtable_record_id]) {
      return airtableVideoMaps.byRecordId[p.airtable_record_id];
    }

    const normalize = (value?: string | null) =>
      (value || '').toLowerCase().replace(/\s+/g, ' ').trim();

    const titleKey = normalize(p.title);
    const hookKey = normalize(p.hook);

    if (titleKey && airtableVideoMaps.byTitle[titleKey]) {
      return airtableVideoMaps.byTitle[titleKey];
    }
    if (hookKey && airtableVideoMaps.byTitle[hookKey]) {
      return airtableVideoMaps.byTitle[hookKey];
    }

    return '';
  };

  return (
    <AppLayout title={t('content.title')}>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-foreground">{t('content.title')}</h1>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => { fetchProjects(); refreshAirtable(); }}
              disabled={loading || airtableLoading}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              רענון
            </Button>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Button
                      onClick={() => setShowGenerateDialog(true)}
                      disabled={generating || !connection || !hasVideos}
                      className="gradient-primary text-primary-foreground gap-2 rounded-xl"
                    >
                      {generating ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}
                      {generating ? t('content.creating') : t('content.createWeekly')}
                    </Button>
                  </span>
                </TooltipTrigger>
                {!hasVideos && connection && (
                  <TooltipContent side="bottom">
                    <p>{t('content.uploadVideosFirst')}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        {/* No connection */}
        {!connection && (
          <Card className="glass">
            <CardContent className="p-8 text-center">
              <p className="text-muted-foreground">{t('content.connectFirst')}</p>
            </CardContent>
          </Card>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Empty state */}
        {!loading && sortedProjects.length === 0 && connection && (
          <Card className="glass">
            <CardContent className="p-12 text-center space-y-4">
              <Film className="h-16 w-16 mx-auto text-muted-foreground opacity-30" />
              <p className="text-muted-foreground">{t('content.noProjects')}</p>
            </CardContent>
          </Card>
        )}

        {/* Video Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedProjects.map(project => {
            const url = getVideoUrl(project);
            const statusInfo = STATUS_MAP[project.status || 'draft'] || STATUS_MAP.draft;

            return (
              <Card key={project.id} className="glass overflow-hidden group">
                {/* Video */}
                {url ? (
                  <div className="relative aspect-[9/16] bg-muted">
                    <video
                      src={url}
                      className="w-full h-full object-contain bg-black"
                      controls
                      preload="metadata"
                      playsInline
                      muted
                    />
                  </div>
                ) : (
                  <div className="aspect-video bg-muted flex items-center justify-center">
                    <Film className="h-12 w-12 text-muted-foreground opacity-30" />
                  </div>
                )}

                <CardContent className="p-4 space-y-3">
                  {/* Title + Status */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-foreground truncate">
                      {project.title || project.hook || t('content.noTitle')}
                    </span>
            <Badge className={`text-xs shrink-0 ${statusInfo.color}`}>
                      {t(statusInfo.label as any)}
                    </Badge>
                  </div>

                  {/* Caption */}
                  {project.caption && (
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {project.caption}
                    </p>
                  )}

                  {/* Magnet */}
                  {project.magnet_name && (
                    <Badge variant="secondary" className="text-xs">
                      {project.magnet_name}
                    </Badge>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-2 pt-1">
                    {project.status === 'draft' && (
                      <>
                        <Button
                          size="sm"
                          className="flex-1 gap-1 bg-primary hover:bg-primary/90 text-primary-foreground"
                          onClick={() => handleApprove(project)}
                        >
                          <Check className="h-3.5 w-3.5" />
                          {t('content.approveBtn')}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          className="flex-1 gap-1"
                          onClick={() => setRejectingProject(project)}
                        >
                          <X className="h-3.5 w-3.5" />
                          {t('content.reject')}
                        </Button>
                      </>
                    )}
                    {project.status === 'approved' && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 gap-1"
                        onClick={() => handleReturnToDraft(project)}
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                        {t('content.returnToDraft')}
                      </Button>
                    )}
                    {project.status === 'rejected' && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 gap-1"
                        onClick={() => handleReturnToDraft(project)}
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                        {t('content.returnToDraft')}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Reject Dialog */}
      <Dialog open={!!rejectingProject} onOpenChange={open => !open && setRejectingProject(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('content.rejectProject')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('content.rejectionReason')}</Label>
              <Textarea
                placeholder={t('content.rejectionPlaceholder')}
                value={rejectionNotes}
                onChange={e => setRejectionNotes(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setRejectingProject(null)}>
                {t('content.close')}
              </Button>
              <Button variant="destructive" onClick={handleReject}>
                {t('content.reject')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Generate Content Dialog */}
      <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('content.createNewTitle')}</DialogTitle>
          </DialogHeader>

          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setMode('automatic')}
                className={`p-4 rounded-xl border-2 text-center transition-all ${
                  mode === 'automatic'
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <Wand2 className="h-6 w-6 mx-auto mb-2 text-primary" />
                <p className="font-medium text-foreground">{t('content.automatic')}</p>
                <p className="text-xs text-muted-foreground mt-1">{t('content.automaticDesc')}</p>
              </button>
              <button
                onClick={() => setMode('manual')}
                className={`p-4 rounded-xl border-2 text-center transition-all ${
                  mode === 'manual'
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <SlidersHorizontal className="h-6 w-6 mx-auto mb-2 text-primary" />
                <p className="font-medium text-foreground">{t('content.manual')}</p>
                <p className="text-xs text-muted-foreground mt-1">{t('content.manualDesc')}</p>
              </button>
            </div>

            <div className="space-y-2">
              <Label>{t('content.reelsCount')}</Label>
              <Select value={String(quantity)} onValueChange={val => setQuantity(Number(val))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">{t('content.reels3')}</SelectItem>
                  <SelectItem value="5">{t('content.reels5')}</SelectItem>
                  <SelectItem value="7">{t('content.reels7')}</SelectItem>
                  <SelectItem value="10">{t('content.reels10')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {mode === 'manual' && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
                <div className="space-y-2">
                  <Label>{t('content.contentType')}</Label>
                  <Select
                    value={manualParams.content_type || ''}
                    onValueChange={val => setManualParams(p => ({ ...p, content_type: val }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('content.chooseContentType')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="חשיפה">{t('content.exposure')}</SelectItem>
                      <SelectItem value="מכירה">{t('content.sales')}</SelectItem>
                      <SelectItem value="מעורב">{t('content.mixed')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{t('content.currentTopic')}</Label>
                  <Input
                    placeholder={t('content.topicPlaceholder')}
                    value={manualParams.topic || ''}
                    onChange={e => setManualParams(p => ({ ...p, topic: e.target.value }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t('content.magnet')}</Label>
                  {magnetsLoading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {t('content.loadingMagnets')}
                    </div>
                  ) : magnets.length === 0 ? (
                    <p className="text-sm text-muted-foreground">{t('content.noMagnets')}</p>
                  ) : (
                    <Select
                      value={manualParams.magnet_id || ''}
                      onValueChange={val => {
                        const magnet = magnets.find(m => m.id === val);
                        setManualParams(p => ({
                          ...p,
                          magnet_id: val,
                          magnet_name: magnet?.name || '',
                        }));
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('content.chooseMagnet')} />
                      </SelectTrigger>
                      <SelectContent>
                        {magnets.map(magnet => (
                          <SelectItem key={magnet.id} value={magnet.id}>
                            {magnet.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            )}

            <Button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full gradient-primary text-primary-foreground gap-2"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {t('content.createWeekly')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
