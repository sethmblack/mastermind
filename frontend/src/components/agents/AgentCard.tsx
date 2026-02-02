import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PersonaDetailDialog } from './PersonaDetailDialog';
import { FileText, Sparkles } from 'lucide-react';
import type { PersonaSummary } from '@/types';

interface AgentCardProps {
  persona: PersonaSummary;
}

export function AgentCard({ persona }: AgentCardProps) {
  const [dialogOpen, setDialogOpen] = useState<'prompt' | 'skills' | null>(null);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <div
            className={cn(
              'px-3 py-1.5 rounded cursor-pointer transition-colors',
              'hover:bg-accent/50 text-sm'
            )}
          >
            {persona.display_name}
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={() => setDialogOpen('prompt')}>
            <FileText className="h-4 w-4 mr-2" />
            View Prompt
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setDialogOpen('skills')}>
            <Sparkles className="h-4 w-4 mr-2" />
            View Skills
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <PersonaDetailDialog
        personaName={dialogOpen ? persona.name : null}
        initialTab={dialogOpen || 'prompt'}
        onClose={() => setDialogOpen(null)}
      />
    </>
  );
}
