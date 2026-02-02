import { useStore } from '@/store';
import { SessionControls } from '@/components/controls/SessionControls';
import { SessionSelector } from '@/components/controls/SessionSelector';
import { OrchestratorControls } from '@/components/controls/OrchestratorControls';
import { BudgetMetrics } from '@/components/controls/BudgetMetrics';
import { RoundIndicator } from '@/components/controls/RoundIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Settings,
  MessageSquarePlus,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export function LeftSidebar() {
  const { currentSession, setSettingsOpen } = useStore();

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <h1 className="font-semibold text-lg gradient-text">
              Mastermind
            </h1>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Session Selector - Always visible */}
          <section>
            <h3 className="text-sm font-medium mb-3 text-muted-foreground">
              Sessions
            </h3>
            <SessionSelector />
          </section>

          <Separator />

          {currentSession ? (
            <>
              {/* Round Indicator */}
              <section>
                <h3 className="text-sm font-medium mb-3 text-muted-foreground">
                  Discussion Round
                </h3>
                <RoundIndicator />
              </section>

              <Separator />

              {/* Session Controls */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    Session
                  </h3>
                  <span className="text-sm font-medium truncate max-w-[60%] text-right" title={currentSession.name}>
                    {currentSession.name}
                  </span>
                </div>
                <SessionControls />
              </section>

              <Separator />

              {/* Orchestrator Controls */}
              <section>
                <h3 className="text-sm font-medium mb-3 text-muted-foreground">
                  Discussion Controls
                </h3>
                <OrchestratorControls />
              </section>

              <Separator />

              {/* Budget Metrics */}
              <section>
                <h3 className="text-sm font-medium mb-3 text-muted-foreground">
                  Token Usage
                </h3>
                <BudgetMetrics />
              </section>
            </>
          ) : (
            <div className="text-center py-12">
              <MessageSquarePlus className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground text-sm">
                Select personas and create a session to start
              </p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted-foreground text-center">
          265 Expert Personas Available
        </p>
      </div>
    </div>
  );
}
