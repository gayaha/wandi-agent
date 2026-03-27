import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { SendHorizontal, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  sending?: boolean;
}

export default function ChatInput({ onSend, disabled, sending }: ChatInputProps) {
  const [text, setText] = useState('');
  const { t, direction } = useLanguage();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    if (!text.trim() || disabled || sending) return;
    onSend(text);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [text, disabled, sending, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }
  };

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-md p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <Textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => { setText(e.target.value); handleInput(); }}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.inputPlaceholder')}
          disabled={disabled || sending}
          rows={1}
          className="resize-none min-h-[40px] max-h-[120px] flex-1"
          dir={direction}
        />
        <Button
          onClick={handleSend}
          disabled={!text.trim() || disabled || sending}
          size="icon"
          className="shrink-0 h-10 w-10 gradient-primary text-primary-foreground rounded-xl"
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SendHorizontal className={`h-4 w-4 ${direction === 'rtl' ? 'rotate-180' : ''}`} />
          )}
        </Button>
      </div>
    </div>
  );
}
