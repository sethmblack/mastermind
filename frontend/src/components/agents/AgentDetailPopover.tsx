import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { personasApi } from '@/lib/api';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Info, Quote, Sparkles, BookOpen, Loader2 } from 'lucide-react';

interface AgentDetailPopoverProps {
  personaName: string;
}

export function AgentDetailPopover({ personaName }: AgentDetailPopoverProps) {
  const [open, setOpen] = useState(false);

  const { data: persona, isLoading } = useQuery({
    queryKey: ['persona', personaName],
    queryFn: () => personasApi.get(personaName),
    enabled: open,
  });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={(e) => e.stopPropagation()}
        >
          <Info className="h-3 w-3" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-96"
        align="start"
        onClick={(e) => e.stopPropagation()}
      >
        {isLoading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : persona ? (
          <ScrollArea className="h-[400px]">
            <div className="space-y-4">
              {/* Header */}
              <div>
                <h3 className="font-semibold text-lg">{persona.display_name}</h3>
                <div className="flex gap-2 mt-1">
                  {persona.domain && (
                    <Badge variant="secondary">{persona.domain}</Badge>
                  )}
                  {persona.era && (
                    <Badge variant="outline">{persona.era}</Badge>
                  )}
                </div>
              </div>

              {/* Voice Profile */}
              {persona.voice_profile && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4" />
                      Voice Profile
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {persona.voice_profile}
                    </p>
                  </div>
                </>
              )}

              {/* Skills */}
              {persona.skills.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                      <BookOpen className="h-4 w-4" />
                      Skills ({persona.skills.length})
                    </h4>
                    <div className="space-y-2">
                      {persona.skills.slice(0, 5).map((skill) => (
                        <div
                          key={skill.name}
                          className="text-xs p-2 bg-muted rounded"
                        >
                          <div className="font-medium">{skill.name}</div>
                          <div className="text-muted-foreground mt-1">
                            {skill.use_when}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Quotes */}
              {persona.signature_quotes.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                      <Quote className="h-4 w-4" />
                      Signature Quotes
                    </h4>
                    <div className="space-y-2">
                      {persona.signature_quotes.slice(0, 3).map((quote, i) => (
                        <blockquote
                          key={i}
                          className="text-xs italic text-muted-foreground border-l-2 border-primary pl-3"
                        >
                          "{quote}"
                        </blockquote>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Expertise Summary */}
              {persona.expertise_summary && (
                <>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium mb-2">Expertise</h4>
                    <p className="text-xs text-muted-foreground">
                      {persona.expertise_summary}
                    </p>
                  </div>
                </>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}
