import { useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Loader2, MessageSquare } from 'lucide-react';
import type { ChatMessage } from '@/hooks/useAgentChat';

const TOOL_ICONS: Record<string, string> = {
  searched_profile: '\uD83D\uDD0D',
  created_content: '\u270D\uFE0F',
  analyzed_data: '\uD83D\uDCCA',
  scheduled_post: '\uD83D\uDCC5',
};

interface MessageListProps {
  messages: ChatMessage[];
  sending: boolean;
  messagesLoading: boolean;
  elapsedSeconds: number;
}

function ToolBadges({ tools }: { tools: string[] }) {
  const { t } = useLanguage();
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {tools.map((tool, i) => {
        const icon = TOOL_ICONS[tool] || '\u2699\uFE0F';
        const key = `chat.tools.${tool}` as any;
        const label = t(key) !== key ? t(key) : tool;
        return (
          <Badge key={i} variant="secondary" className="text-[10px] px-1.5 py-0 gap-1 font-normal">
            <span>{icon}</span>
            <span>{label}</span>
          </Badge>
        );
      })}
    </div>
  );
}

function ThinkingIndicator({ elapsedSeconds }: { elapsedSeconds: number }) {
  const { t } = useLanguage();
  const elapsed = elapsedSeconds > 0
    ? elapsedSeconds >= 60
      ? ` (${Math.floor(elapsedSeconds / 60)} דקות)`
      : ` (${elapsedSeconds} שניות)`
    : '';
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-ss-sm px-4 py-3 bg-card border text-card-foreground">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">{t('chat.thinking')}{elapsed}</span>
        </div>
      </div>
    </div>
  );
}

export default function MessageList({ messages, sending, messagesLoading, elapsedSeconds }: MessageListProps) {
  const { t } = useLanguage();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  if (messagesLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (messages.length === 0 && !sending) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground px-4">
        <MessageSquare className="h-12 w-12 opacity-30" />
        <p className="text-sm text-center">{t('chat.emptyState')}</p>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="max-w-3xl mx-auto p-4 space-y-4">
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          return (
            <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  isUser
                    ? 'bg-primary text-primary-foreground rounded-ee-sm'
                    : 'bg-card border text-card-foreground rounded-ss-sm'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                {!isUser && msg.tools_used && msg.tools_used.length > 0 && (
                  <ToolBadges tools={msg.tools_used} />
                )}
                {!isUser && msg.total_duration_ms && (
                  <span className="text-[10px] text-muted-foreground mt-1 block">
                    {(msg.total_duration_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {sending && <ThinkingIndicator elapsedSeconds={elapsedSeconds} />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
