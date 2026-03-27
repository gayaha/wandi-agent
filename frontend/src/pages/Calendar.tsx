import { useState, useMemo } from 'react';
import AppLayout from '@/components/AppLayout';
import CreatePostModal from '@/components/CreatePostModal';
import { useMetaConnection } from '@/hooks/useMetaConnection';
import { useCalendarPosts } from '@/hooks/useCalendarPosts';
import { useLanguage } from '@/contexts/LanguageContext';
import { translations } from '@/lib/translations';
import { Button } from '@/components/ui/button';
import { ChevronRight, ChevronLeft, Loader2, Plus, Clock, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

type ScheduledPost = any;

const statusDot: Record<string, string> = {
  pending: 'bg-primary',
  published: 'bg-success',
  failed: 'bg-destructive',
  draft: 'bg-muted-foreground',
  publishing: 'bg-warning',
};

const CalendarPage = () => {
  const { connection } = useMetaConnection();
  const { t, language } = useLanguage();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [createPostOpen, setCreatePostOpen] = useState(false);

  const DAYS = (translations[language]['calendar.days'] as unknown as string[]);
  const MONTHS = (translations[language]['calendar.months'] as unknown as string[]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const { postsByDate, loading, refetch } = useCalendarPosts(year, month);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const days: (number | null)[] = [];
    for (let i = 0; i < firstDay; i++) days.push(null);
    for (let i = 1; i <= daysInMonth; i++) days.push(i);
    return days;
  }, [year, month]);

  const prev = () => setCurrentDate(new Date(year, month - 1, 1));
  const next = () => setCurrentDate(new Date(year, month + 1, 1));

  const selectedDayPosts = selectedDay ? (postsByDate[selectedDay] || []) : [];

  return (
    <AppLayout title={t('calendar.title')} onNewPost={connection ? () => setCreatePostOpen(true) : undefined}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <div className="lg:col-span-2 glass p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">{MONTHS[month]} {year}</h3>
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" onClick={next}><ChevronRight className="h-5 w-5" /></Button>
              <Button variant="ghost" size="icon" onClick={prev}><ChevronLeft className="h-5 w-5" /></Button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {DAYS.map((d) => (
              <div key={d} className="text-center text-xs text-muted-foreground py-2 font-medium">{d}</div>
            ))}
            {calendarDays.map((day, i) => {
              if (day === null) return <div key={`e-${i}`} />;
              const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const dayPosts = postsByDate[dateStr] || [];
              const isToday = new Date().toISOString().startsWith(dateStr);
              const isSelected = selectedDay === dateStr;

              return (
                <button
                  key={dateStr}
                  onClick={() => setSelectedDay(dateStr)}
                  className={cn(
                    'relative aspect-square flex flex-col items-center justify-center rounded-lg text-sm transition-all hover:bg-secondary/50',
                    isToday && 'ring-1 ring-primary',
                    isSelected && 'bg-primary/20 ring-1 ring-primary'
                  )}
                >
                  <span>{day}</span>
                  {dayPosts.length > 0 && (
                    <div className="flex gap-0.5 mt-1">
                      {dayPosts.slice(0, 3).map((p: any) => (
                        <div key={p.id} className={cn('h-1.5 w-1.5 rounded-full', statusDot[p.status] || 'bg-muted-foreground')} />
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Day detail */}
        <div className="glass p-6 space-y-4">
          <h3 className="font-semibold">
            {selectedDay ? format(new Date(selectedDay), 'dd/MM/yyyy') : t('calendar.selectDay')}
          </h3>
          {selectedDay && selectedDayPosts.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">{t('calendar.noPostsOnDay')}</p>
          )}
          <div className="space-y-3">
            {selectedDayPosts.map((post: any) => (
              <div key={post.id} className="p-3 rounded-lg bg-secondary/30 space-y-2">
                {post.media_url && <img src={post.media_url} className="w-full h-32 object-cover rounded-md" alt="" />}
                <p className="text-sm line-clamp-2">{post.caption || t('dashboard.noCaption')}</p>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{format(new Date(post.scheduled_at), 'HH:mm')}</span>
                  <span className={cn(
                    'px-2 py-0.5 rounded-full text-xs font-medium',
                    post.status === 'published' ? 'bg-success/20 text-success' :
                    post.status === 'failed' ? 'bg-destructive/20 text-destructive' :
                    'bg-primary/20 text-primary'
                  )}>
                    {post.status === 'published' ? t('calendar.published') : post.status === 'failed' ? t('calendar.failed') : post.status === 'pending' ? t('calendar.scheduled') : post.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Floating FAB */}
      {connection && (
        <>
          <button
            onClick={() => setCreatePostOpen(true)}
            className="fixed bottom-6 left-6 lg:hidden gradient-primary text-primary-foreground h-14 w-14 rounded-full shadow-lg flex items-center justify-center hover:scale-105 transition-transform"
          >
            <Plus className="h-6 w-6" />
          </button>
          <CreatePostModal
            open={createPostOpen}
            onOpenChange={setCreatePostOpen}
            connectionId={connection.id}
            onSuccess={refetch}
          />
        </>
      )}
    </AppLayout>
  );
};

export default CalendarPage;
