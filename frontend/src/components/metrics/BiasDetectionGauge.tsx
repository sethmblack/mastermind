import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import { AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react';

interface BiasDetectionGaugeProps {
  sessionId: number;
}

export function BiasDetectionGauge({ sessionId }: BiasDetectionGaugeProps) {
  const { data: biasCheck } = useQuery({
    queryKey: ['bias', sessionId],
    queryFn: () => analyticsApi.checkBias(sessionId),
    refetchInterval: 15000, // Refresh every 15 seconds
  });

  if (!biasCheck) return null;

  const riskScore = biasCheck.groupthink_risk_score * 100;

  const Icon =
    biasCheck.risk_level === 'low'
      ? CheckCircle
      : biasCheck.risk_level === 'medium'
      ? AlertTriangle
      : AlertCircle;

  const riskColor =
    biasCheck.risk_level === 'low'
      ? 'text-green-500'
      : biasCheck.risk_level === 'medium'
      ? 'text-yellow-500'
      : 'text-red-500';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Groupthink Risk</span>
        <div className={cn('flex items-center gap-1', riskColor)}>
          <Icon className="h-4 w-4" />
          <span className="text-sm font-bold capitalize">
            {biasCheck.risk_level}
          </span>
        </div>
      </div>

      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full transition-all',
            biasCheck.risk_level === 'low' && 'bg-green-500',
            biasCheck.risk_level === 'medium' && 'bg-yellow-500',
            biasCheck.risk_level === 'high' && 'bg-red-500'
          )}
          style={{ width: `${riskScore}%` }}
        />
      </div>

      {biasCheck.indicators.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">Indicators:</span>
          <ul className="text-xs space-y-1">
            {biasCheck.indicators.slice(0, 3).map((indicator, i) => (
              <li key={i} className="text-muted-foreground flex items-start gap-1">
                <span className="text-yellow-500">•</span>
                {indicator}
              </li>
            ))}
          </ul>
        </div>
      )}

      {biasCheck.recommendations.length > 0 && (
        <div className="text-xs p-2 bg-muted rounded">
          <span className="font-medium">Suggestion: </span>
          {biasCheck.recommendations[0]}
        </div>
      )}
    </div>
  );
}
