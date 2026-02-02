import { useRef, useEffect, useState, useCallback } from 'react';
import { useStore } from '@/store';
import { ConversationFlow } from './ConversationFlow';
import { UserInputArea } from './UserInputArea';
import { WelcomeScreen } from './WelcomeScreen';
import { McpWaitingIndicator } from './McpWaitingIndicator';
import { OrchestratorStatus } from './OrchestratorStatus';
import { GenerationStatus } from './GenerationStatus';
import { sessionsApi } from '@/lib/api';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ChatArea() {
  const { currentSession, messages, streamingMessages, setMessages } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Refresh messages from API
  const refreshMessages = useCallback(async () => {
    if (!currentSession) return;
    // Don't refresh if actively streaming - WebSocket handles real-time updates
    if (streamingMessages.size > 0) return;
    setIsRefreshing(true);
    try {
      const msgs = await sessionsApi.getMessages(currentSession.id);
      setMessages(msgs);
    } catch (e) {
      console.error('Failed to refresh messages:', e);
    } finally {
      setIsRefreshing(false);
    }
  }, [currentSession, setMessages, streamingMessages.size]);

  // NOTE: Removed auto-refresh while thinking - it conflicts with WebSocket streaming
  // The WebSocket already handles real-time message delivery via persona_chunk and persona_done events
  // Auto-refresh was causing duplicate messages and "restart" behavior

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
        <div className="flex items-center justify-between">
          <div className="w-8" /> {/* Spacer for centering */}
          <h2 className="font-semibold">{currentSession.name}</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={refreshMessages}
            disabled={isRefreshing}
            title="Refresh messages"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        {currentSession.problem_statement && (
          <p className="text-sm text-muted-foreground text-center mt-1 max-w-2xl mx-auto">
            {currentSession.problem_statement}
          </p>
        )}
      </div>

      {/* Orchestrator Status (shows when Claude Code is processing) */}
      <OrchestratorStatus />

      {/* Generation Status (shows when any persona is thinking/streaming) */}
      <GenerationStatus />

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-4"
        onScroll={handleScroll}
      >
        <ConversationFlow />
      </div>

      {/* MCP Waiting Indicator */}
      <McpWaitingIndicator />

      {/* Input Area */}
      <UserInputArea />
    </div>
  );
}
