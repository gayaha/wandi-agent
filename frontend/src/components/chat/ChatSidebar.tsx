import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus } from 'lucide-react';
import type { ChatSession } from '@/hooks/useAgentChat';

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  sessionsLoading: boolean;
  className?: string;
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export default function ChatSidebar({ sessions, activeSessionId, onSelectSession, onNewChat, sessionsLoading, className }: ChatSidebarProps) {
  const { t } = useLanguage();

  return (
    <div className={className ?? "w-72 border-e border-border bg-background/50 flex flex-col shrink-0 hidden md:flex"}>
      <div className="p-3">
        <Button onClick={onNewChat} className="w-full gradient-primary text-primary-foreground gap-2 rounded-xl">
          <Plus className="h-4 w-4" />
          {t('chat.newChat')}
        </Button>
      </div>

      <div className="px-3 pb-1">
        <span className="text-xs text-muted-foreground font-medium">{t('chat.sessions')}</span>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-2 pb-2 space-y-1">
          {sessionsLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))
          ) : sessions.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">{t('chat.noSessions')}</p>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`w-full text-start px-3 py-2.5 rounded-lg transition-colors text-sm truncate ${
                  activeSessionId === s.id
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-muted/50 text-foreground'
                }`}
              >
                <span className="block truncate font-medium">{s.title || 'Untitled'}</span>
                <span className="text-[10px] text-muted-foreground">{formatRelativeTime(s.created_at)}</span>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
