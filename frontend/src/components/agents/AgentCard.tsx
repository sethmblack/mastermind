import { useStore } from '@/store';
import { cn, slugToTitle } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { AgentDetailPopover } from './AgentDetailPopover';
import type { PersonaSummary } from '@/types';
import { User } from 'lucide-react';

interface AgentCardProps {
  persona: PersonaSummary;
}

export function AgentCard({ persona }: AgentCardProps) {
  const {
    selectedPersonas,
    addSelectedPersona,
    removeSelectedPersona,
    currentSession,
  } = useStore();

  const isSelected = selectedPersonas.some((p) => p.name === persona.name);
  const isInSession = currentSession?.personas.some(
    (p) => p.persona_name === persona.name
  );
  const canSelect = selectedPersonas.length < 5 || isSelected;

  const handleToggle = () => {
    if (isInSession) return; // Can't change if already in session

    if (isSelected) {
      removeSelectedPersona(persona.name);
    } else if (canSelect) {
      addSelectedPersona(persona);
    }
  };

  return (
    <div
      className={cn(
        'p-3 mx-2 my-1 rounded-lg border transition-colors cursor-pointer',
        isSelected
          ? 'border-primary bg-primary/10'
          : 'border-border hover:border-primary/50 hover:bg-accent/50',
        isInSession && 'border-green-500/50 bg-green-500/10 cursor-default',
        !canSelect && !isSelected && 'opacity-50 cursor-not-allowed'
      )}
      onClick={handleToggle}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <Checkbox
          checked={isSelected || isInSession}
          disabled={isInSession || (!canSelect && !isSelected)}
          className="mt-1"
        />

        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <User className="h-5 w-5 text-primary" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-sm truncate">
              {persona.display_name}
            </h4>
            <AgentDetailPopover personaName={persona.name} />
          </div>

          {persona.domain && (
            <Badge variant="secondary" className="mt-1 text-xs">
              {slugToTitle(persona.domain)}
            </Badge>
          )}

          {persona.voice_preview && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {persona.voice_preview}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
