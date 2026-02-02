import { useStore } from '@/store';
import { cn } from '@/lib/utils';
import {
  MessageCircle,
  MessagesSquare,
  CheckCircle2,
} from 'lucide-react';
import { useMemo } from 'react';

export function RoundIndicator() {
  const { currentSession, messages } = useStore();

  // Calculate current round from messages
  const { currentRound, maxRounds, minRounds } = useMemo(() => {
    if (!currentSession) {
      return { currentRound: 1, maxRounds: 3, minRounds: 3 };
    }

    const config = currentSession.config || {};
    const maxRounds = config.max_rounds || 3;
    const minRounds = config.min_rounds || 3;

    // Get the latest turn number from messages
    const turnMessages = messages.filter(m => m.turn_number > 0);
    if (turnMessages.length === 0) {
      return { currentRound: 1, maxRounds, minRounds };
    }

    const latestTurn = Math.max(...turnMessages.map(m => m.turn_number));
    const currentTurnMessages = messages.filter(m => m.turn_number === latestTurn);

    // Calculate round from messages in current turn
    const roundNumbers = currentTurnMessages
      .filter(m => m.role === 'assistant' && m.round_number)
      .map(m => m.round_number || 1);

    const highestRound = roundNumbers.length > 0 ? Math.max(...roundNumbers) : 1;

    // Check if all personas have responded in the highest round
    const personaCount = currentSession.personas?.length || 0;
    const responsesInHighestRound = currentTurnMessages.filter(
      m => m.role === 'assistant' && (m.round_number || 1) === highestRound
    ).length;

    // If all personas responded, we're waiting for next round or complete
    const currentRound = responsesInHighestRound >= personaCount
      ? Math.min(highestRound + 1, maxRounds + 1)
      : highestRound;

    return { currentRound: Math.min(currentRound, maxRounds), maxRounds, minRounds };
  }, [currentSession, messages]);

  if (!currentSession) return null;

  const isComplete = currentRound > maxRounds;
  // Map round 1 to 0%, final round to 100%
  const progress = isComplete ? 100 : maxRounds <= 1 ? 100 : ((currentRound - 1) / (maxRounds - 1)) * 100;

  const getRoundLabel = (round: number) => {
    if (round === 1) return 'Initial';
    if (round === maxRounds) return 'Final';
    return `Round ${round}`;
  };

  const getRoundDescription = (round: number) => {
    if (isComplete) return 'Discussion complete';
    if (round === 1) return 'Initial responses to the topic';
    if (round === maxRounds) return 'Final synthesis and conclusions';
    return 'Personas responding to each other';
  };

  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="relative h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn(
            "absolute h-full transition-all duration-500",
            isComplete
              ? "bg-green-500"
              : "bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Round indicators */}
      <div className="flex justify-between">
        {Array.from({ length: maxRounds }, (_, i) => i + 1).map((round) => {
          const isActive = round === currentRound && !isComplete;
          const isCompleted = round < currentRound || isComplete;

          const Icon = round === 1
            ? MessageCircle
            : round === maxRounds
              ? CheckCircle2
              : MessagesSquare;

          return (
            <div
              key={round}
              className={cn(
                'flex flex-col items-center gap-1 transition-all',
                isActive && 'scale-110',
                isCompleted && 'text-primary',
                !isActive && !isCompleted && 'text-muted-foreground opacity-50'
              )}
              title={getRoundLabel(round)}
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
                {getRoundLabel(round)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Current round info */}
      <div className="text-center space-y-1">
        <p className="text-sm font-medium">
          {isComplete ? (
            <span className="text-green-600 dark:text-green-400">Discussion Complete</span>
          ) : (
            <>Round {currentRound} of {maxRounds}</>
          )}
        </p>
        <p className="text-xs text-muted-foreground">
          {getRoundDescription(currentRound)}
        </p>
      </div>

      {/* Min rounds info */}
      {minRounds > 1 && (
        <p className="text-[10px] text-muted-foreground text-center">
          Minimum {minRounds} rounds required
        </p>
      )}
    </div>
  );
}
