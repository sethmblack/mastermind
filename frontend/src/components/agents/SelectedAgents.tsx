import { useStore } from '@/store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, User } from 'lucide-react';
import { getPersonaColor } from '@/lib/utils';

export function SelectedAgents() {
  const { selectedPersonas, removeSelectedPersona, currentSession } = useStore();

  // If in a session, show session personas instead
  const personasToShow = currentSession
    ? currentSession.personas.map((p) => ({
        name: p.persona_name,
        display_name: p.display_name || p.persona_name,
        color: p.color,
      }))
    : selectedPersonas.map((p, i) => ({
        name: p.name,
        display_name: p.display_name,
        color: getPersonaColor(i),
      }));

  if (personasToShow.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          {currentSession ? 'Session Personas' : 'Selected'}
        </span>
        {!currentSession && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs"
            onClick={() => {
              selectedPersonas.forEach((p) => removeSelectedPersona(p.name));
            }}
          >
            Clear all
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {personasToShow.map((persona) => (
          <Badge
            key={persona.name}
            variant="secondary"
            className="flex items-center gap-1 pr-1"
            style={{
              borderColor: persona.color,
              borderWidth: 2,
            }}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: persona.color }}
            />
            <span className="text-xs">{persona.display_name}</span>
            {!currentSession && (
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 ml-1 hover:bg-transparent"
                onClick={(e) => {
                  e.stopPropagation();
                  removeSelectedPersona(persona.name);
                }}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </Badge>
        ))}
      </div>
    </div>
  );
}
