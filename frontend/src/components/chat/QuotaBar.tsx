import { useLanguage } from '@/contexts/LanguageContext';
import { Progress } from '@/components/ui/progress';
import type { Quota } from '@/hooks/useAgentChat';

interface QuotaBarProps {
  quota: Quota | null;
}

export default function QuotaBar({ quota }: QuotaBarProps) {
  const { t } = useLanguage();

  if (!quota) return null;

  const { used, limit, remaining } = quota.messages;
  const percent = limit > 0 ? (used / limit) * 100 : 0;
  const exceeded = remaining <= 0;

  const label = t('chat.quota').replace('{used}', String(used)).replace('{limit}', String(limit));

  return (
    <div className="px-4 py-2 border-b border-border bg-background/60 backdrop-blur-sm flex items-center gap-3">
      <Progress value={percent} className="h-2 flex-1 max-w-48" />
      <span className={`text-xs whitespace-nowrap ${exceeded ? 'text-destructive font-medium' : 'text-muted-foreground'}`}>
        {exceeded ? t('chat.quotaExceeded') : label}
      </span>
    </div>
  );
}
