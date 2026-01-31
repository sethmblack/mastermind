import { useRef, useEffect, useState } from 'react';
import { useStore } from '@/store';
import { ConversationFlow } from './ConversationFlow';
import { UserInputArea } from './UserInputArea';
import { WelcomeScreen } from './WelcomeScreen';
import { ScrollArea } from '@/components/ui/scroll-area';

export function ChatArea() {
  const { currentSession, messages, streamingMessages } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingMessages, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const isAtBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight < 100;
    setAutoScroll(isAtBottom);
  };

  if (!currentSession) {
    return <WelcomeScreen />;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card/50">
        <h2 className="font-semibold text-center">{currentSession.name}</h2>
        {currentSession.problem_statement && (
          <p className="text-sm text-muted-foreground text-center mt-1 max-w-2xl mx-auto">
            {currentSession.problem_statement}
          </p>
        )}
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-4"
        onScroll={handleScroll}
      >
        <ConversationFlow />
      </div>

      {/* Input Area */}
      <UserInputArea />
    </div>
  );
}
