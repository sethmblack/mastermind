import { useState } from 'react';
import { useStore } from '@/store';
import { Button } from '@/components/ui/button';
import { Copy, Check, Sparkles } from 'lucide-react';

export function McpWaitingIndicator() {
  const { currentSession, thinkingPersonas } = useStore();
  const [copied, setCopied] = useState(false);

  // Check if any persona is "thinking" (waiting for response)
  const waitingPersonas = Array.from(thinkingPersonas);

  const isMcpMode = currentSession?.config?.mcp_mode;

  if (!isMcpMode || waitingPersonas.length === 0) {
    return null;
  }

  const prompt = `Generate responses for session ${currentSession.id}`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-4 mb-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
      <div className="flex items-start gap-3">
        <Sparkles className="h-5 w-5 text-blue-400 mt-0.5 animate-pulse" />
        <div className="flex-1">
          <p className="text-sm font-medium text-blue-400">
            Waiting for Claude Code
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {waitingPersonas.length} persona{waitingPersonas.length > 1 ? 's' : ''} waiting: {waitingPersonas.join(', ')}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 px-3 py-2 bg-background/50 rounded text-xs font-mono">
              {prompt}
            </code>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="shrink-0"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Paste this to Claude Code to generate responses
          </p>
        </div>
      </div>
    </div>
  );
}
