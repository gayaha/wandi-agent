import { useState, useRef, useCallback } from 'react';
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
import { Switch } from '@/components/ui/switch';
import { usePublishPost } from '@/hooks/usePublishPost';
import { Upload, Loader2, X, AlertCircle, Plus, Image as ImageIcon, Film, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { validateMediaFile, validateImageDimensions, validateCarouselFiles } from '@/lib/media-validation';
import { toast } from 'sonner';
import { useLanguage } from '@/contexts/LanguageContext';

interface CreatePostModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectionId: string;
  onSuccess?: () => void;
}

interface MediaItem {
  file: File;
  preview: string;
  type: 'image' | 'video';
}

export default function CreatePostModal({ open, onOpenChange, connectionId, onSuccess }: CreatePostModalProps) {
  const { t } = useLanguage();
  const [step, setStep] = useState<1 | 2>(1);
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [caption, setCaption] = useState('');
  const [scheduleMode, setScheduleMode] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const addFileInputRef = useRef<HTMLInputElement>(null);
  const { publish, loading } = usePublishPost();

  const resetState = useCallback(() => {
    setStep(1);
    setMediaItems([]);
    setCaption('');
    setValidationError(null);
    setScheduleMode(false);
    setScheduleDate('');
    setScheduleTime('');
  }, []);

  const addFiles = (fileList: FileList | File[]) => {
    setValidationError(null);
    const files = Array.from(fileList);

    for (const f of files) {
      const validation = validateMediaFile(f);
      if (!validation.valid) {
        setValidationError(validation.error!);
        toast.error(validation.error!);
        return;
      }
    }

    // Read previews for all files
    const newItems: MediaItem[] = [];
    let processed = 0;

    files.forEach((f) => {
      const validation = validateMediaFile(f);
      const reader = new FileReader();
      reader.onloadend = () => {
        newItems.push({ file: f, preview: reader.result as string, type: validation.mediaType });
        processed++;

        if (processed === files.length) {
          setMediaItems(prev => {
            const combined = [...prev, ...newItems];
            if (combined.length > 10) {
              toast.error(t('createPost.maxCarousel'));
              return prev;
            }
            return combined;
          });
          setStep(2);

          // Validate image dimensions for image files
          for (const item of newItems) {
            if (item.type === 'image') {
              const img = new Image();
              img.onload = () => {
                const dimValidation = validateImageDimensions(img.width, img.height);
                if (!dimValidation.valid) {
                  setValidationError(dimValidation.error!);
                  toast.warning(dimValidation.error!);
                }
              };
              img.src = item.preview;
            }
          }
        }
      };
      reader.readAsDataURL(f);
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const removeItem = (index: number) => {
    setMediaItems(prev => {
      const next = prev.filter((_, i) => i !== index);
      if (next.length === 0) setStep(1);
      return next;
    });
  };

  const resolvedMediaType = mediaItems.length > 1
    ? 'carousel' as const
    : mediaItems.length === 1
      ? mediaItems[0].type
      : 'image' as const;

  const handleSubmit = async () => {
    if (mediaItems.length === 0) return;

    if (mediaItems.length > 1) {
      const carouselValidation = validateCarouselFiles(mediaItems.map(m => m.file));
      if (!carouselValidation.valid) {
        toast.error(carouselValidation.error!);
        return;
      }
    }

    let scheduleAt: string | undefined;
    if (scheduleMode && scheduleDate && scheduleTime) {
      scheduleAt = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();
    }

    const result = await publish({
      connectionId,
      files: mediaItems.map(m => m.file),
      caption,
      scheduleAt,
      mediaType: resolvedMediaType,
    });

    if (result) {
      onSuccess?.();
      onOpenChange(false);
      resetState();
    }
  };

  const typeLabel = resolvedMediaType === 'carousel' ? t('media.carousel') : resolvedMediaType === 'video' ? t('media.video') : t('media.image');
  const TypeIcon = resolvedMediaType === 'carousel' ? Layers : resolvedMediaType === 'video' ? Film : ImageIcon;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) resetState(); onOpenChange(v); }}>
      <DialogContent className="glass border-border bg-card sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            {step === 1 ? t('createPost.uploadMedia') : t('createPost.postDetails')}
          </DialogTitle>
        </DialogHeader>

        {step === 1 ? (
          <div
            className={cn(
              'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
              dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
            )}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-2">{t('createPost.dragFiles')}</p>
            <p className="text-sm text-muted-foreground/60">{t('createPost.selectMultiple')}</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,video/mp4,video/quicktime"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
              }}
            />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Media type badge */}
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/15 text-primary text-xs font-medium">
                <TypeIcon className="h-3.5 w-3.5" />
                {typeLabel} ({mediaItems.length} {mediaItems.length === 1 ? t('createPost.item') : t('createPost.items')})
              </span>
            </div>

            {/* Media previews */}
            <div className={cn(
              'grid gap-2',
              mediaItems.length === 1 ? 'grid-cols-1' : 'grid-cols-3'
            )}>
              {mediaItems.map((item, i) => (
                <div key={i} className="relative group">
                  {item.type === 'video' ? (
                    <video
                      src={item.preview}
                      className={cn(
                        'w-full object-cover rounded-lg',
                        mediaItems.length === 1 ? 'h-48' : 'h-24'
                      )}
                    />
                  ) : (
                    <img
                      src={item.preview}
                      alt=""
                      className={cn(
                        'w-full object-cover rounded-lg',
                        mediaItems.length === 1 ? 'h-48' : 'h-24'
                      )}
                    />
                  )}
                  <button
                    onClick={() => removeItem(i)}
                    className="absolute top-1 left-1 p-0.5 rounded-full bg-background/80 hover:bg-background opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                  {item.type === 'video' && (
                    <Film className="absolute bottom-1 right-1 h-4 w-4 text-white drop-shadow" />
                  )}
                </div>
              ))}

              {/* Add more button */}
              {mediaItems.length < 10 && (
                <button
                  onClick={() => addFileInputRef.current?.click()}
                  className={cn(
                    'border-2 border-dashed border-border rounded-lg flex items-center justify-center hover:border-primary/50 transition-colors',
                    mediaItems.length === 1 ? 'h-48' : 'h-24'
                  )}
                >
                  <Plus className="h-6 w-6 text-muted-foreground" />
                </button>
              )}
            </div>

            <input
              ref={addFileInputRef}
              type="file"
              accept="image/jpeg,image/png,video/mp4,video/quicktime"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
              }}
            />

            {validationError && (
              <div className="flex items-center gap-2 text-sm text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{validationError}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label>{t('createPost.caption')}</Label>
              <Textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder={t('createPost.captionPlaceholder')}
                className="bg-secondary/50 border-border min-h-[100px] resize-none"
                maxLength={2200}
              />
              <p className="text-xs text-muted-foreground text-left" dir="ltr">
                {caption.length}/2200
              </p>
            </div>

            <div className="flex items-center justify-between">
              <Label>{t('createPost.scheduleDate')}</Label>
              <Switch checked={scheduleMode} onCheckedChange={setScheduleMode} />
            </div>

            {scheduleMode && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">{t('createPost.date')}</Label>
                  <Input
                    type="date"
                    value={scheduleDate}
                    onChange={(e) => setScheduleDate(e.target.value)}
                    className="bg-secondary/50 border-border"
                    dir="ltr"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('createPost.time')}</Label>
                  <Input
                    type="time"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    className="bg-secondary/50 border-border"
                    dir="ltr"
                  />
                </div>
              </div>
            )}

            <Button
              onClick={handleSubmit}
              disabled={loading || mediaItems.length === 0}
              className="w-full gradient-primary text-primary-foreground font-semibold h-11"
            >
              {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
              {scheduleMode ? t('createPost.schedulePost') : t('createPost.publishNow')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
