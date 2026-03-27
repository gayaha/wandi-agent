import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAgentChat } from '@/hooks/useAgentChat';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import ChatHeader from '@/components/chat/ChatHeader';
import ChatSidebar from '@/components/chat/ChatSidebar';
import QuotaBar from '@/components/chat/QuotaBar';
import MessageList from '@/components/chat/MessageList';
import ChatInput from '@/components/chat/ChatInput';

export default function ChatPage() {
  const { direction } = useLanguage();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const {
    sessions,
    sessionsLoading,
    activeSessionId,
    messages,
    messagesLoading,
    quota,
    sending,
    elapsedSeconds,
    error,
    selectSession,
    startNewChat,
    sendMessage,
  } = useAgentChat();

  const quotaExceeded = quota ? quota.messages.remaining <= 0 : false;

  const handleSelectSession = (id: string) => {
    selectSession(id);
    setSidebarOpen(false);
  };

  const handleNewChat = () => {
    startNewChat();
    setSidebarOpen(false);
  };

  const sidebarContent = (
    <ChatSidebar
      sessions={sessions}
      activeSessionId={activeSessionId}
      onSelectSession={handleSelectSession}
      onNewChat={handleNewChat}
      sessionsLoading={sessionsLoading}
    />
  );

  return (
    <div dir={direction} className="h-screen flex flex-col bg-background">
      <ChatHeader onToggleSidebar={() => setSidebarOpen(true)} />

      <div className="flex-1 flex overflow-hidden">
        {/* Desktop sidebar */}
        {sidebarContent}

        {/* Mobile sidebar */}
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetContent side={direction === 'rtl' ? 'right' : 'left'} className="p-0 w-72">
            <ChatSidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectSession={handleSelectSession}
              onNewChat={handleNewChat}
              sessionsLoading={sessionsLoading}
              className="w-full flex flex-col h-full bg-background"
            />
          </SheetContent>
        </Sheet>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <QuotaBar quota={quota} />

          {error && (
            <div className="px-4 py-2 bg-destructive/10 text-destructive text-xs text-center">
              {error}
            </div>
          )}

          <MessageList
            messages={messages}
            sending={sending}
            messagesLoading={messagesLoading}
            elapsedSeconds={elapsedSeconds}
          />

          <ChatInput
            onSend={sendMessage}
            disabled={quotaExceeded}
            sending={sending}
          />
        </div>
      </div>
    </div>
  );
}
