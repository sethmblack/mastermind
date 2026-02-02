import { useState } from 'react';
import { useStore } from '@/store';
import { AgentList } from '@/components/agents/AgentList';
import { AgentSearch, SortMode } from '@/components/agents/AgentSearch';
import { Button } from '@/components/ui/button';
import { Users, Plus, User } from 'lucide-react';
import { slugToTitle } from '@/lib/utils';

export function RightSidebar() {
  const { currentSession, thinkingPersonas, streamingMessages } = useStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>('alphabetical');

  // If there's an active session, show session personas instead of the full list
  if (currentSession) {
    return (
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            <h2 className="font-semibold">Session Personas</h2>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {currentSession.personas.length} participant{currentSession.personas.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Session Personas */}
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {currentSession.personas.map((persona) => {
            const isThinking = thinkingPersonas.has(persona.persona_name);
            const isStreaming = streamingMessages.has(persona.persona_name);
            const isActive = isThinking || isStreaming;

            return (
              <div
                key={persona.persona_name}
                className="p-3 rounded-lg border bg-card transition-all"
                style={{
                  borderColor: isActive ? persona.color : undefined,
                  boxShadow: isActive ? `0 0 10px ${persona.color}30` : undefined,
                }}
              >
                <div className="flex items-center gap-3">
                  {/* Avatar */}
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: persona.color + '20' }}
                  >
                    <User className="h-5 w-5" style={{ color: persona.color }} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="font-medium text-sm truncate"
                        style={{ color: persona.color }}
                      >
                        {persona.display_name || slugToTitle(persona.persona_name)}
                      </span>
                      {isActive && (
                        <span className="flex-shrink-0">
                          <span
                            className="inline-block w-2 h-2 rounded-full animate-pulse"
                            style={{ backgroundColor: persona.color }}
                          />
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {isThinking && !isStreaming && 'Thinking...'}
                      {isStreaming && 'Typing...'}
                      {!isActive && (
                        <span className="flex items-center gap-1">
                          <span className="px-1.5 py-0.5 rounded bg-muted text-[10px] font-medium uppercase">
                            {persona.provider}
                          </span>
                          <span className="truncate">{persona.model}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Session Info */}
        <div className="p-4 border-t border-border text-xs text-muted-foreground">
          <div>Mode: {currentSession.turn_mode.replace('_', ' ')}</div>
        </div>
      </div>
    );
  }

  // No active session - show persona browser with Create Session button
  return (
    <div className="flex flex-col h-full">
      {/* Header with Create Session button */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            <h2 className="font-semibold">Personas</h2>
          </div>
        </div>

        {/* Create Session Button */}
        <Button
          className="w-full mb-3"
          onClick={() => {
            const event = new CustomEvent('open-new-session-modal');
            window.dispatchEvent(event);
          }}
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Session
        </Button>

        {/* Search */}
        <AgentSearch
          value={searchQuery}
          onChange={setSearchQuery}
          selectedDomain={selectedDomain}
          onDomainChange={setSelectedDomain}
          sortMode={sortMode}
          onSortChange={setSortMode}
        />
      </div>

      {/* Agent List - names only, click for menu */}
      <div className="flex-1 overflow-hidden">
        <AgentList
          searchQuery={searchQuery}
          selectedDomain={selectedDomain}
          sortMode={sortMode}
        />
      </div>
    </div>
  );
}
