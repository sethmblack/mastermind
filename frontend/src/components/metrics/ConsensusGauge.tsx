import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ConsensusGaugeProps {
  sessionId: number;
}

export function ConsensusGauge({ sessionId }: ConsensusGaugeProps) {
  const { data: metrics } = useQuery({
    queryKey: ['consensus', sessionId],
    queryFn: () => analyticsApi.getConsensus(sessionId),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (!metrics) return null;

  const agreementPercent = metrics.average_agreement * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Consensus Level</span>
        <span
          className={cn(
            'text-sm font-bold',
            agreementPercent >= 70 && 'text-green-500',
            agreementPercent >= 40 && agreementPercent < 70 && 'text-yellow-500',
            agreementPercent < 40 && 'text-red-500'
          )}
        >
          {Math.round(agreementPercent)}%
        </span>
      </div>

      <div className="relative h-4 bg-muted rounded-full overflow-hidden">
        {/* Disagreement (red) */}
        <div
          className="absolute h-full bg-red-500/50"
          style={{ width: `${100 - agreementPercent}%`, left: 0 }}
        />
        {/* Agreement (green) */}
        <div
          className="absolute h-full bg-green-500"
          style={{ width: `${agreementPercent}%`, right: 0 }}
        />
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <div className="font-medium text-green-500">
            {metrics.votes_by_type.agree}
          </div>
          <div className="text-muted-foreground">Agree</div>
        </div>
        <div>
          <div className="font-medium text-yellow-500">
            {metrics.votes_by_type.abstain}
          </div>
          <div className="text-muted-foreground">Abstain</div>
        </div>
        <div>
          <div className="font-medium text-red-500">
            {metrics.votes_by_type.disagree}
          </div>
          <div className="text-muted-foreground">Disagree</div>
        </div>
      </div>

      {metrics.most_contested && (
        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Most contested:</span>{' '}
          {metrics.most_contested.slice(0, 50)}...
        </div>
      )}
    </div>
  );
}
