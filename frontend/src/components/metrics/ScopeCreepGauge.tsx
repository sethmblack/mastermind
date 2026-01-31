import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Target, TrendingUp, AlertTriangle } from 'lucide-react';

interface ScopeCreepGaugeProps {
  sessionId: number;
}

export function ScopeCreepGauge({ sessionId }: ScopeCreepGaugeProps) {
  const { data: scopeCheck } = useQuery({
    queryKey: ['scope', sessionId],
    queryFn: () => analyticsApi.checkScopeCreep(sessionId),
    refetchInterval: 15000,
  });

  if (!scopeCheck) return null;

  const driftScore = scopeCheck.scope_creep_score * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Scope Drift</span>
        <div
          className={cn(
            'flex items-center gap-1 text-sm font-bold',
            scopeCheck.risk_level === 'low' && 'text-green-500',
            scopeCheck.risk_level === 'medium' && 'text-yellow-500',
            scopeCheck.risk_level === 'high' && 'text-red-500'
          )}
        >
          {scopeCheck.risk_level === 'low' ? (
            <Target className="h-4 w-4" />
          ) : scopeCheck.risk_level === 'medium' ? (
            <TrendingUp className="h-4 w-4" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          <span className="capitalize">{scopeCheck.risk_level}</span>
        </div>
      </div>

      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full transition-all',
            scopeCheck.risk_level === 'low' && 'bg-green-500',
            scopeCheck.risk_level === 'medium' && 'bg-yellow-500',
            scopeCheck.risk_level === 'high' && 'bg-red-500'
          )}
          style={{ width: `${driftScore}%` }}
        />
      </div>

      {scopeCheck.original_problem && (
        <div className="text-xs">
          <span className="text-muted-foreground">Original focus: </span>
          <span className="font-medium">
            {scopeCheck.original_problem.slice(0, 80)}
            {scopeCheck.original_problem.length > 80 && '...'}
          </span>
        </div>
      )}

      {scopeCheck.scope_creep_instances.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">
            Drift instances detected:
          </span>
          <ul className="text-xs space-y-1">
            {scopeCheck.scope_creep_instances.slice(0, 2).map((instance, i) => (
              <li
                key={i}
                className="text-muted-foreground flex items-start gap-1"
              >
                <span className="text-yellow-500">•</span>
                {instance.content.slice(0, 60)}...
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
