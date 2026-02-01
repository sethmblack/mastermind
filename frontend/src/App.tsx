import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout/AppLayout';
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { ChatArea } from '@/components/chat/ChatArea';
import { SettingsModal } from '@/components/modals/SettingsModal';
import { NewSessionModal } from '@/components/modals/NewSessionModal';
import { useStore } from '@/store';
import { personasApi, sessionsApi } from '@/lib/api';
import { wsClient } from '@/lib/websocket';
import type { WSEvent } from '@/types';

const SESSION_STORAGE_KEY = 'multi-agent-collab-session-id';

function App() {
  const {
    currentSession,
    setCurrentSession,
    setMessages,
    addMessage,
    startStreaming,
    appendStreamingChunk,
    completeStreaming,
    setPersonaThinking,
    updateTokenUsage,
    updateSessionPhase,
    setDiscussionActive,
    setOrchestratorStatus,
    updateOrchestratorTokenUsage,
  } = useStore();

  // Prefetch personas count
  useQuery({
    queryKey: ['personas', 'count'],
    queryFn: personasApi.getCount,
  });

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
    if (savedSessionId && !currentSession) {
      const sessionId = parseInt(savedSessionId, 10);
      if (!isNaN(sessionId)) {
        sessionsApi.get(sessionId)
          .then((session) => {
            setCurrentSession(session);
            // Load messages for the session
            sessionsApi.getMessages(sessionId).then(setMessages).catch(console.error);
          })
          .catch((e) => {
            console.error('Failed to restore session:', e);
            localStorage.removeItem(SESSION_STORAGE_KEY);
          });
      }
    }
  }, []);

  // Save session ID to localStorage when it changes
  useEffect(() => {
    if (currentSession) {
      localStorage.setItem(SESSION_STORAGE_KEY, currentSession.id.toString());
    }
  }, [currentSession?.id]);

  // WebSocket event handling
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      switch (event.type) {
        case 'connected':
          console.log('Connected to session');
          break;

        case 'user_message':
          addMessage({
            id: Date.now(),
            role: 'user',
            content: event.data.content as string,
            turn_number: event.data.turn_number as number,
            metadata: {},
            created_at: event.timestamp,
          });
          break;

        case 'persona_thinking':
          setPersonaThinking(event.data.persona_name as string, true);
          startStreaming(event.data.persona_name as string);
          break;

        case 'persona_chunk':
          appendStreamingChunk(
            event.data.persona_name as string,
            event.data.chunk as string
          );
          break;

        case 'persona_done':
          setPersonaThinking(event.data.persona_name as string, false);
          completeStreaming(
            event.data.persona_name as string,
            event.data.content as string
          );
          addMessage({
            id: Date.now(),
            persona_name: event.data.persona_name as string,
            role: 'assistant',
            content: event.data.content as string,
            turn_number: (event.data.turn_number as number) || 1,
            round_number: (event.data.round_number as number) || 1,
            metadata: {},
            created_at: event.timestamp,
          });
          updateTokenUsage(event.data.persona_name as string, {
            input_tokens: event.data.input_tokens as number,
            output_tokens: event.data.output_tokens as number,
            total_tokens:
              (event.data.input_tokens as number) + (event.data.output_tokens as number),
            cost: 0,
          });
          break;

        case 'phase_change':
          updateSessionPhase(event.data.new_phase as any);
          break;

        case 'token_update':
          // Additional token updates
          break;

        case 'orchestrator_status':
          setOrchestratorStatus({
            status: event.data.status as string,
            persona_name: event.data.persona_name as string | undefined,
            round_number: event.data.round_number as number | undefined,
            details: event.data.details as string | undefined,
            timestamp: event.timestamp,
            input_tokens: event.data.input_tokens as number | undefined,
            output_tokens: event.data.output_tokens as number | undefined,
            cache_read_tokens: event.data.cache_read_tokens as number | undefined,
            cache_creation_tokens: event.data.cache_creation_tokens as number | undefined,
          });
          // Update cumulative orchestrator token usage
          if (event.data.input_tokens || event.data.output_tokens || event.data.cache_read_tokens || event.data.cache_creation_tokens) {
            updateOrchestratorTokenUsage({
              input_tokens: event.data.input_tokens as number | undefined,
              output_tokens: event.data.output_tokens as number | undefined,
              cache_read_tokens: event.data.cache_read_tokens as number | undefined,
              cache_creation_tokens: event.data.cache_creation_tokens as number | undefined,
            });
          }
          break;

        case 'error':
          console.error('WebSocket error:', event.data.message);
          break;
      }
    };

    const unsubscribe = wsClient.on('*', handleEvent);
    return () => unsubscribe();
  }, []);

  // Connect to session WebSocket when session changes
  useEffect(() => {
    if (currentSession) {
      wsClient.connect(currentSession.id).catch(console.error);
      setDiscussionActive(currentSession.status === 'active');
    } else {
      wsClient.disconnect();
      setMessages([]);
    }

    return () => {
      wsClient.disconnect();
    };
  }, [currentSession?.id]);

  return (
    <div className="h-screen w-screen overflow-hidden bg-background">
      <AppLayout
        leftSidebar={<LeftSidebar />}
        rightSidebar={<RightSidebar />}
        main={<ChatArea />}
      />
      <SettingsModal />
      <NewSessionModal />
    </div>
  );
}

export default App;
