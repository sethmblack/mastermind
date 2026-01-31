import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout/AppLayout';
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { ChatArea } from '@/components/chat/ChatArea';
import { SettingsModal } from '@/components/modals/SettingsModal';
import { NewSessionModal } from '@/components/modals/NewSessionModal';
import { useStore } from '@/store';
import { personasApi } from '@/lib/api';
import { wsClient } from '@/lib/websocket';
import type { WSEvent } from '@/types';

function App() {
  const {
    currentSession,
    setMessages,
    addMessage,
    startStreaming,
    appendStreamingChunk,
    completeStreaming,
    setPersonaThinking,
    updateTokenUsage,
    updateSessionPhase,
    setDiscussionActive,
  } = useStore();

  // Prefetch personas count
  useQuery({
    queryKey: ['personas', 'count'],
    queryFn: personasApi.getCount,
  });

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
            turn_number: 0,
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
