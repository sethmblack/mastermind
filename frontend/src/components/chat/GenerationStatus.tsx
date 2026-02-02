import { useStore } from '@/store';
import { Loader2, MessageSquare, Sparkles } from 'lucide-react';
import { slugToTitle } from '@/lib/utils';

export function GenerationStatus() {
  const { thinkingPersonas, streamingMessages, currentSession } = useStore();

  // Don't show if MCP mode (use OrchestratorStatus instead)
  if (currentSession?.config?.mcp_mode) {
    return null;
  }

  // Get personas that are thinking (not yet streaming)
  const thinking = Array.from(thinkingPersonas).filter(
    (p) => !streamingMessages.has(p)
  );

  // Get personas that are streaming
  const streaming = Array.from(streamingMessages.keys());

  // Nothing to show
  if (thinking.length === 0 && streaming.length === 0) {
    return null;
  }

  // Get display names for personas
  const getDisplayName = (personaName: string) => {
    const persona = currentSession?.personas.find(
      (p) => p.persona_name === personaName
    );
    return persona?.display_name || slugToTitle(personaName);
  };

  // Get color for persona
  const getColor = (personaName: string) => {
    const persona = currentSession?.personas.find(
      (p) => p.persona_name === personaName
    );
    return persona?.color || '#888';
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-muted/50 border-b border-border text-sm overflow-x-auto">
      {/* Thinking personas */}
      {thinking.map((personaName) => (
        <div
          key={personaName}
          className="flex items-center gap-2 px-3 py-1 rounded-full bg-background/80 border"
          style={{ borderColor: getColor(personaName) + '50' }}
        >
          <Loader2
            className="h-3 w-3 animate-spin"
            style={{ color: getColor(personaName) }}
          />
          <span
            className="font-medium text-xs"
            style={{ color: getColor(personaName) }}
          >
            {getDisplayName(personaName)}
          </span>
          <span className="text-xs text-muted-foreground">thinking...</span>
        </div>
      ))}

      {/* Streaming personas */}
      {streaming.map((personaName) => (
        <div
          key={personaName}
          className="flex items-center gap-2 px-3 py-1 rounded-full bg-background/80 border"
          style={{ borderColor: getColor(personaName) + '50' }}
        >
          <Sparkles
            className="h-3 w-3 animate-pulse"
            style={{ color: getColor(personaName) }}
          />
          <span
            className="font-medium text-xs"
            style={{ color: getColor(personaName) }}
          >
            {getDisplayName(personaName)}
          </span>
          <span className="text-xs text-muted-foreground">typing...</span>
        </div>
      ))}

      {/* Summary */}
      {(thinking.length + streaming.length) > 0 && (
        <div className="flex items-center gap-1 text-muted-foreground ml-auto">
          <MessageSquare className="h-3 w-3" />
          <span className="text-xs">
            {thinking.length + streaming.length} generating
          </span>
        </div>
      )}
    </div>
  );
}
