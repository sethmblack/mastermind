import { useState, useEffect } from 'react';
import { useStore } from '@/store';
import { sessionsApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { turnModeLabels, getPersonaColor } from '@/lib/utils';
import type { TurnMode, PersonaConfig } from '@/types';
import { Loader2, X } from 'lucide-react';

export function NewSessionModal() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [turnMode, setTurnMode] = useState<TurnMode>('round_robin');
  const [isCreating, setIsCreating] = useState(false);

  const {
    selectedPersonas,
    removeSelectedPersona,
    clearSelectedPersonas,
    setCurrentSession,
    setMessages,
  } = useStore();

  // Listen for open event
  useEffect(() => {
    const handleOpen = () => setOpen(true);
    window.addEventListener('open-new-session-modal', handleOpen);
    return () => window.removeEventListener('open-new-session-modal', handleOpen);
  }, []);

  const handleCreate = async () => {
    if (!name.trim() || selectedPersonas.length === 0) return;

    setIsCreating(true);
    try {
      const personas: PersonaConfig[] = selectedPersonas.map((p, i) => ({
        persona_name: p.name,
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514',
        role: 'participant',
        color: getPersonaColor(i),
      }));

      const session = await sessionsApi.create({
        name: name.trim(),
        problem_statement: problemStatement.trim() || undefined,
        personas,
        turn_mode: turnMode,
      });

      setCurrentSession(session);
      setMessages([]);
      clearSelectedPersonas();
      setOpen(false);

      // Reset form
      setName('');
      setProblemStatement('');
      setTurnMode('round_robin');
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create New Session</DialogTitle>
          <DialogDescription>
            Set up a collaboration session with your selected personas
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Session Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Session Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Product Strategy Discussion"
            />
          </div>

          {/* Problem Statement */}
          <div className="space-y-2">
            <Label htmlFor="problem">Problem Statement (optional)</Label>
            <Textarea
              id="problem"
              value={problemStatement}
              onChange={(e) => setProblemStatement(e.target.value)}
              placeholder="What should the personas discuss?"
              rows={3}
            />
          </div>

          {/* Turn Mode */}
          <div className="space-y-2">
            <Label>Discussion Mode</Label>
            <Select
              value={turnMode}
              onValueChange={(v) => setTurnMode(v as TurnMode)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(turnModeLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Selected Personas */}
          <div className="space-y-2">
            <Label>Personas ({selectedPersonas.length}/5)</Label>
            <div className="flex flex-wrap gap-2">
              {selectedPersonas.map((persona, i) => (
                <Badge
                  key={persona.name}
                  variant="secondary"
                  className="flex items-center gap-1"
                  style={{
                    borderColor: getPersonaColor(i),
                    borderWidth: 2,
                  }}
                >
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: getPersonaColor(i) }}
                  />
                  {persona.display_name}
                  <button
                    className="ml-1 hover:text-destructive"
                    onClick={() => removeSelectedPersona(persona.name)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            {selectedPersonas.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Select personas from the sidebar
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={!name.trim() || selectedPersonas.length === 0 || isCreating}
          >
            {isCreating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Session'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
