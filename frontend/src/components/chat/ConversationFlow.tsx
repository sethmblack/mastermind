import { useStore } from '@/store';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

export function ConversationFlow() {
  const { messages, thinkingPersonas, currentSession } = useStore();

  // Get persona colors map
  const personaColors: Record<string, string> = {};
  currentSession?.personas.forEach((p) => {
    personaColors[p.persona_name] = p.color || '#888';
  });

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* Existing messages */}
      {messages.map((message, index) => (
        <MessageBubble
          key={message.id || index}
          message={message}
          color={message.persona_name ? personaColors[message.persona_name] : undefined}
          displayName={
            message.persona_name
              ? currentSession?.personas.find(
                  (p) => p.persona_name === message.persona_name
                )?.display_name || message.persona_name
              : undefined
          }
          animate={false}
        />
      ))}

      {/* Thinking indicators - shown while waiting for response */}
      {Array.from(thinkingPersonas).map((personaName) => (
        <TypingIndicator
          key={personaName}
          personaName={personaName}
          color={personaColors[personaName]}
          displayName={
            currentSession?.personas.find(
              (p) => p.persona_name === personaName
            )?.display_name || personaName
          }
        />
      ))}
    </div>
  );
}
