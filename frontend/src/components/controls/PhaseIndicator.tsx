import { useStore } from '@/store';
import { cn, phaseLabels } from '@/lib/utils';
import { wsClient } from '@/lib/websocket';
import type { SessionPhase } from '@/types';
import {
  Search,
  Lightbulb,
  Scale,
  CheckCircle2,
  Zap,
  FileText,
} from 'lucide-react';

const phases: { key: SessionPhase; icon: typeof Search }[] = [
  { key: 'discovery', icon: Search },
  { key: 'ideation', icon: Lightbulb },
  { key: 'evaluation', icon: Scale },
  { key: 'decision', icon: CheckCircle2 },
  { key: 'action', icon: Zap },
  { key: 'synthesis', icon: FileText },
];

export function PhaseIndicator() {
  const { currentSession } = useStore();

  if (!currentSession) return null;

  const currentPhaseIndex = phases.findIndex(
    (p) => p.key === currentSession.phase
  );

  const handlePhaseClick = (phase: SessionPhase) => {
    wsClient.changePhase(phase);
  };

  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="relative h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="absolute h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-500"
          style={{
            width: `${((currentPhaseIndex + 1) / phases.length) * 100}%`,
          }}
        />
      </div>

      {/* Phase icons */}
      <div className="flex justify-between">
        {phases.map((phase, index) => {
          const Icon = phase.icon;
          const isActive = phase.key === currentSession.phase;
          const isCompleted = index < currentPhaseIndex;

          return (
            <button
              key={phase.key}
              className={cn(
                'flex flex-col items-center gap-1 transition-all',
                isActive && 'scale-110',
                isCompleted && 'text-primary',
                !isActive && !isCompleted && 'text-muted-foreground opacity-50'
              )}
              onClick={() => handlePhaseClick(phase.key)}
              title={phaseLabels[phase.key]}
            >
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center transition-colors',
                  isActive && 'bg-primary text-primary-foreground',
                  isCompleted && 'bg-primary/20',
                  !isActive && !isCompleted && 'bg-muted'
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <span className="text-[10px] font-medium">
                {phaseLabels[phase.key]}
              </span>
            </button>
          );
        })}
      </div>

      {/* Current phase description */}
      <p className="text-xs text-muted-foreground text-center">
        {currentSession.phase === 'discovery' &&
          'Understanding the problem deeply'}
        {currentSession.phase === 'ideation' &&
          'Generating diverse ideas and approaches'}
        {currentSession.phase === 'evaluation' &&
          'Critically assessing proposed solutions'}
        {currentSession.phase === 'decision' &&
          'Working toward consensus'}
        {currentSession.phase === 'action' &&
          'Defining concrete next steps'}
        {currentSession.phase === 'synthesis' &&
          'Summarizing insights and decisions'}
      </p>
    </div>
  );
}
