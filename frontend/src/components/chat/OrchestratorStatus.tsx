import { useStore } from '@/store';
import { Bot, Loader2, CheckCircle, AlertCircle, Clock, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMemo } from 'react';

const STATUS_CONFIG: Record<string, { icon: typeof Bot; color: string; label: string }> = {
  checking: {
    icon: Clock,
    color: 'text-blue-500',
    label: 'Checking for pending work...',
  },
  generating: {
    icon: Sparkles,
    color: 'text-purple-500',
    label: 'Generating response',
  },
  submitting: {
    icon: Loader2,
    color: 'text-amber-500',
    label: 'Submitting response',
  },
  waiting: {
    icon: Clock,
    color: 'text-muted-foreground',
    label: 'Waiting for next round',
  },
  complete: {
    icon: CheckCircle,
    color: 'text-green-500',
    label: 'Complete',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    label: 'Error',
  },
  idle: {
    icon: Bot,
    color: 'text-muted-foreground',
    label: 'Idle',
  },
};

export function OrchestratorStatus() {
  const { orchestratorStatus, currentSession } = useStore();

  // Only show if MCP mode is enabled
  const isMcpMode = currentSession?.config?.mcp_mode;

  // Format the status message
  const statusMessage = useMemo(() => {
    if (!orchestratorStatus) return null;

    const config = STATUS_CONFIG[orchestratorStatus.status] || STATUS_CONFIG.idle;
    let message = config.label;

    if (orchestratorStatus.persona_name) {
      if (orchestratorStatus.status === 'generating') {
        message = `Generating ${orchestratorStatus.persona_name}'s response`;
      } else if (orchestratorStatus.status === 'submitting') {
        message = `Submitting ${orchestratorStatus.persona_name}'s response`;
      }
    }

    if (orchestratorStatus.round_number) {
      message += ` (Round ${orchestratorStatus.round_number})`;
    }

    if (orchestratorStatus.details) {
      message += ` - ${orchestratorStatus.details}`;
    }

    return { ...config, message };
  }, [orchestratorStatus]);

  if (!isMcpMode || !orchestratorStatus || orchestratorStatus.status === 'idle') {
    return null;
  }

  const config = statusMessage || STATUS_CONFIG.idle;
  const IconComponent = config.icon;
  const isAnimating = ['checking', 'generating', 'submitting'].includes(orchestratorStatus.status);

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-muted/50 border-b border-border text-sm">
      <Bot className="h-4 w-4 text-purple-500" />
      <span className="text-muted-foreground">Orchestrator:</span>
      <IconComponent
        className={cn(
          'h-4 w-4',
          config.color,
          isAnimating && 'animate-spin'
        )}
      />
      <span className={config.color}>{config.message}</span>
    </div>
  );
}
