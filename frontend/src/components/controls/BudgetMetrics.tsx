import { useStore } from '@/store';
import { Progress } from '@/components/ui/progress';
import { formatNumber, formatCurrency } from '@/lib/utils';

export function BudgetMetrics() {
  const { totalTokenUsage, tokenUsage, currentSession } = useStore();

  // Budget limits (from config or defaults)
  const budgetLimit = 100000; // Default budget
  const utilization = (totalTokenUsage.total_tokens / budgetLimit) * 100;

  return (
    <div className="space-y-4">
      {/* Total Usage */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Total Tokens</span>
          <span className="font-medium">
            {formatNumber(totalTokenUsage.total_tokens)}
          </span>
        </div>
        <Progress value={Math.min(utilization, 100)} className="h-2" />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{Math.round(utilization)}% used</span>
          <span>{formatNumber(budgetLimit)} budget</span>
        </div>
      </div>

      {/* Cost */}
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Estimated Cost</span>
        <span className="font-medium">{formatCurrency(totalTokenUsage.cost)}</span>
      </div>

      {/* Breakdown by Persona */}
      {currentSession && tokenUsage.size > 0 && (
        <div className="space-y-2">
          <span className="text-sm text-muted-foreground">By Persona</span>
          <div className="space-y-1">
            {currentSession.personas.map((persona) => {
              const usage = tokenUsage.get(persona.persona_name);
              if (!usage) return null;

              const personaUtil = (usage.total_tokens / budgetLimit) * 100;

              return (
                <div key={persona.persona_name} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span
                      className="truncate"
                      style={{ color: persona.color }}
                    >
                      {persona.display_name || persona.persona_name}
                    </span>
                    <span className="text-muted-foreground ml-2">
                      {formatNumber(usage.total_tokens)}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(personaUtil, 100)}
                    className="h-1"
                    style={{
                      // @ts-ignore - Custom CSS property for color
                      '--progress-color': persona.color,
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Input/Output breakdown */}
      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border">
        <div>
          <div className="text-xs text-muted-foreground">Input</div>
          <div className="text-sm font-medium">
            {formatNumber(totalTokenUsage.input_tokens)}
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Output</div>
          <div className="text-sm font-medium">
            {formatNumber(totalTokenUsage.output_tokens)}
          </div>
        </div>
      </div>
    </div>
  );
}
