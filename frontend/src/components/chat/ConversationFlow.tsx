import { useStore } from '@/store';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { StreamingMessage } from './StreamingMessage';

export function ConversationFlow() {
  const { messages, thinkingPersonas, streamingMessages, currentSession } = useStore();

  // Get persona colors map
  const personaColors: Record<string, string> = {};
  currentSession?.personas.forEach((p) => {
    personaColors[p.persona_name] = p.color || '#888';
  });

  // Get display name helper
  const getDisplayName = (personaName: string) => {
    return currentSession?.personas.find(
      (p) => p.persona_name === personaName
    )?.display_name || personaName;
  };

  // Personas that are thinking but not yet streaming
  const thinkingOnly = Array.from(thinkingPersonas).filter(
    (p) => !streamingMessages.has(p)
  );

  // Personas that are actively streaming content
  const streaming = Array.from(streamingMessages.entries());

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* Existing messages */}
      {messages.map((message, index) => (
        <MessageBubble
          key={message.id || index}
          message={message}
          color={message.persona_name ? personaColors[message.persona_name] : undefined}
          displayName={
            message.persona_name ? getDisplayName(message.persona_name) : undefined
          }
          animate={false}
        />
      ))}

      {/* Thinking indicators - shown while waiting for first token */}
      {thinkingOnly.map((personaName) => (
        <TypingIndicator
          key={`thinking-${personaName}`}
          personaName={personaName}
          color={personaColors[personaName]}
          displayName={getDisplayName(personaName)}
        />
      ))}

      {/* Streaming messages - shown while receiving tokens */}
      {streaming.map(([personaName, data]) => (
        <StreamingMessage
          key={`streaming-${personaName}`}
          personaName={personaName}
          content={data.content}
          color={personaColors[personaName]}
          displayName={getDisplayName(personaName)}
        />
      ))}
    </div>
  );
}
