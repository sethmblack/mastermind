import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { personasApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, ChevronLeft } from 'lucide-react';

interface PersonaDetailDialogProps {
  personaName: string | null;
  initialTab?: 'prompt' | 'skills';
  onClose: () => void;
}

export function PersonaDetailDialog({
  personaName,
  initialTab = 'prompt',
  onClose,
}: PersonaDetailDialogProps) {
  const [tab, setTab] = useState(initialTab);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);

  const { data: persona, isLoading: loadingPersona } = useQuery({
    queryKey: ['persona', personaName],
    queryFn: () => personasApi.get(personaName!),
    enabled: !!personaName,
  });

  const { data: promptData, isLoading: loadingPrompt } = useQuery({
    queryKey: ['persona-prompt', personaName],
    queryFn: () => personasApi.getPrompt(personaName!),
    enabled: !!personaName && tab === 'prompt',
  });

  const { data: skillPrompt, isLoading: loadingSkillPrompt } = useQuery({
    queryKey: ['skill-prompt', selectedSkill],
    queryFn: () => personasApi.getSkillPrompt(selectedSkill!),
    enabled: !!selectedSkill,
  });

  const isLoading = loadingPersona || (tab === 'prompt' && loadingPrompt);

  // Reset selected skill when dialog closes or persona changes
  const handleClose = () => {
    setSelectedSkill(null);
    onClose();
  };

  // Convert skill name to slug format for API
  const getSkillSlug = (skillName: string) => {
    return skillName.toLowerCase().replace(/\s+/g, '-');
  };

  return (
    <Dialog open={!!personaName} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selectedSkill ? (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSkill(null)}
                  className="mr-2 -ml-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                {skillPrompt?.display_name || selectedSkill}
              </>
            ) : (
              <>
                {persona?.display_name || personaName}
                {persona?.domain && (
                  <Badge variant="secondary" className="text-xs">
                    {persona.domain}
                  </Badge>
                )}
              </>
            )}
          </DialogTitle>
        </DialogHeader>

        {/* Show skill prompt if a skill is selected */}
        {selectedSkill ? (
          loadingSkillPrompt ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <ScrollArea className="h-[55vh]">
              <pre className="text-sm whitespace-pre-wrap font-mono bg-muted p-4 rounded-lg">
                {skillPrompt?.prompt || 'No prompt available'}
              </pre>
            </ScrollArea>
          )
        ) : isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Tabs value={tab} onValueChange={(v) => setTab(v as 'prompt' | 'skills')}>
            <TabsList>
              <TabsTrigger value="prompt">System Prompt</TabsTrigger>
              <TabsTrigger value="skills">
                Skills {persona?.skills.length ? `(${persona.skills.length})` : ''}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="prompt" className="mt-4">
              <ScrollArea className="h-[50vh]">
                <pre className="text-sm whitespace-pre-wrap font-mono bg-muted p-4 rounded-lg">
                  {promptData?.full_prompt || 'No prompt available'}
                </pre>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="skills" className="mt-4">
              <ScrollArea className="h-[50vh]">
                {persona?.skills.length ? (
                  <div className="space-y-2">
                    {persona.skills.map((skill) => (
                      <button
                        key={skill.name}
                        onClick={() => setSelectedSkill(getSkillSlug(skill.name))}
                        className="w-full text-left p-4 border rounded-lg bg-card hover:bg-accent transition-colors"
                      >
                        <h4 className="font-medium text-sm">{skill.name}</h4>
                        <p className="text-xs text-muted-foreground mt-1">
                          <span className="font-medium">Trigger:</span> {skill.trigger}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          <span className="font-medium">Use when:</span> {skill.use_when}
                        </p>
                        <p className="text-xs text-primary mt-2">Click to view full prompt →</p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">
                    No skills defined for this persona
                  </p>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
