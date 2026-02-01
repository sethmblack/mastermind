import { useStore } from '@/store';
import { cn, slugToTitle } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { AgentDetailPopover } from './AgentDetailPopover';
import type { PersonaSummary } from '@/types';

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

  // Create tooltip text
  const tooltipText = persona.description || persona.voice_preview?.split('\n')[0] || `${persona.display_name} - AI Persona`;

  return (
    <div
      className={cn(
        'px-2 py-1 rounded border transition-colors cursor-pointer',
        isSelected
          ? 'border-primary bg-primary/10'
          : 'border-transparent hover:border-primary/50 hover:bg-accent/50',
        isInSession && 'border-green-500/50 bg-green-500/10 cursor-default',
        !canSelect && !isSelected && 'opacity-50 cursor-not-allowed'
      )}
      onClick={handleToggle}
      title={tooltipText}
    >
      <div className="flex items-center gap-2">
        {/* Checkbox */}
        <Checkbox
          checked={isSelected || isInSession}
          disabled={isInSession || (!canSelect && !isSelected)}
          className="h-4 w-4"
        />

        {/* Content */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className="text-sm truncate">{persona.display_name}</span>
          {persona.domain && (
            <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4 shrink-0">
              {slugToTitle(persona.domain)}
            </Badge>
          )}
        </div>

        {/* Info button */}
        <AgentDetailPopover personaName={persona.name} />
      </div>
    </div>
  );
}
