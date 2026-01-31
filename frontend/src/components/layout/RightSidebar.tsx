import { useState } from 'react';
import { useStore } from '@/store';
import { AgentList } from '@/components/agents/AgentList';
import { AgentSearch } from '@/components/agents/AgentSearch';
import { SelectedAgents } from '@/components/agents/SelectedAgents';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Users, Plus } from 'lucide-react';

export function RightSidebar() {
  const { selectedPersonas, currentSession } = useStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [newSessionModalOpen, setNewSessionModalOpen] = useState(false);

  const showCreateButton = selectedPersonas.length > 0 && !currentSession;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            <h2 className="font-semibold">Personas</h2>
          </div>
          <Badge variant="secondary">{selectedPersonas.length}/5</Badge>
        </div>
        <AgentSearch
          value={searchQuery}
          onChange={setSearchQuery}
          selectedDomain={selectedDomain}
          onDomainChange={setSelectedDomain}
        />
      </div>

      {/* Selected Agents */}
      {selectedPersonas.length > 0 && (
        <>
          <div className="p-4 border-b border-border">
            <SelectedAgents />
            {showCreateButton && (
              <Button
                className="w-full mt-3"
                onClick={() => {
                  // Trigger new session modal
                  const event = new CustomEvent('open-new-session-modal');
                  window.dispatchEvent(event);
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Session
              </Button>
            )}
          </div>
        </>
      )}

      {/* Agent List */}
      <ScrollArea className="flex-1">
        <AgentList
          searchQuery={searchQuery}
          selectedDomain={selectedDomain}
        />
      </ScrollArea>
    </div>
  );
}
