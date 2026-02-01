import { useStore } from '@/store';
import { Progress } from '@/components/ui/progress';
import { formatNumber, formatCurrency } from '@/lib/utils';
import { Bot, User, Cpu } from 'lucide-react';
import { useMemo } from 'react';

// Context window limits (approximate for Claude models)
const CONTEXT_LIMITS = {
  persona: 200000,      // 200K context per persona
  orchestrator: 200000, // 200K context for orchestrator (Claude Code)
};

export function BudgetMetrics() {
  const { totalTokenUsage, tokenUsage, currentSession, messages, orchestratorTokenUsage } = useStore();

  // Calculate context usage per persona based on conversation
  const contextUsage = useMemo(() => {
    if (!currentSession || !messages.length) return new Map();

    const usage = new Map<string, number>();

    // Calculate context for each persona (their view of conversation)
    currentSession.personas.forEach((persona) => {
      // Context = all messages they can see + system prompt (~2000 tokens)
      const systemPromptEstimate = 2000;
      const conversationTokens = messages.reduce((acc, msg) => {
        // Estimate tokens: ~4 chars per token
        return acc + Math.ceil(msg.content.length / 4);
      }, 0);
      usage.set(persona.persona_name, systemPromptEstimate + conversationTokens);
    });

    return usage;
  }, [currentSession, messages]);

  // Estimate orchestrator context (all messages + coordination overhead)
  const orchestratorContext = useMemo(() => {
    if (!messages.length) return 0;
    const baseOverhead = 5000; // System instructions, etc.
    const conversationTokens = messages.reduce((acc, msg) => {
      return acc + Math.ceil(msg.content.length / 4);
    }, 0);
    return baseOverhead + conversationTokens * 1.5; // Extra for processing
  }, [messages]);

  // Budget limits (from config or defaults)
  const budgetLimit = 100000; // Default budget
  const utilization = (totalTokenUsage.total_tokens / budgetLimit) * 100;

  return (
    <div className="space-y-4">
      {/* Context Usage Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Cpu className="h-4 w-4 text-primary" />
          Context Usage
        </div>

        {/* Orchestrator Context */}
        <div className="space-y-1 p-2 bg-muted/50 rounded-lg">
          <div className="flex justify-between text-xs">
            <span className="flex items-center gap-1 text-purple-500">
              <Bot className="h-3 w-3" />
              Orchestrator (Claude Code)
            </span>
            <span className="text-muted-foreground">
              {orchestratorTokenUsage.total_tokens > 0
                ? formatNumber(orchestratorTokenUsage.cache_read_tokens)
                : formatNumber(orchestratorContext)
              } / {formatNumber(CONTEXT_LIMITS.orchestrator)}
            </span>
          </div>
          <Progress
            value={Math.min(
              ((orchestratorTokenUsage.total_tokens > 0
                ? orchestratorTokenUsage.cache_read_tokens
                : orchestratorContext) / CONTEXT_LIMITS.orchestrator) * 100,
              100
            )}
            className="h-1.5"
          />
          {orchestratorTokenUsage.total_tokens > 0 && (
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>In: {formatNumber(orchestratorTokenUsage.input_tokens)}</span>
              <span>Out: {formatNumber(orchestratorTokenUsage.output_tokens)}</span>
              <span>Cache: {formatNumber(orchestratorTokenUsage.cache_read_tokens)}</span>
            </div>
          )}
        </div>

        {/* Per-Persona Context */}
        {currentSession && (
          <div className="space-y-2">
            {currentSession.personas.map((persona) => {
              const ctx = contextUsage.get(persona.persona_name) || 0;
              const ctxPercent = (ctx / CONTEXT_LIMITS.persona) * 100;

              return (
                <div key={persona.persona_name} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span
                      className="truncate flex items-center gap-1"
                      style={{ color: persona.color }}
                    >
                      <User className="h-3 w-3" />
                      {persona.display_name || persona.persona_name}
                    </span>
                    <span className="text-muted-foreground">
                      {formatNumber(ctx)} / {formatNumber(CONTEXT_LIMITS.persona)}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(ctxPercent, 100)}
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
        )}
      </div>

      {/* Token Usage Section */}
      <div className="space-y-3 pt-3 border-t border-border">
        <div className="text-sm font-medium">Token Usage</div>

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
            <span className="text-xs text-muted-foreground">Tokens by Persona</span>
            <div className="space-y-1">
              {currentSession.personas.map((persona) => {
                const usage = tokenUsage.get(persona.persona_name);
                if (!usage) return null;

                return (
                  <div key={persona.persona_name} className="flex justify-between text-xs">
                    <span style={{ color: persona.color }}>
                      {persona.display_name || persona.persona_name}
                    </span>
                    <span className="text-muted-foreground">
                      {formatNumber(usage.total_tokens)}
                    </span>
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
    </div>
  );
}
