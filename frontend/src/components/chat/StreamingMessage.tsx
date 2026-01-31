import { slugToTitle } from '@/lib/utils';
import { User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface StreamingMessageProps {
  personaName: string;
  content: string;
  color?: string;
  displayName?: string;
}

export function StreamingMessage({
  personaName,
  content,
  color,
  displayName,
}: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-muted"
        style={color ? { backgroundColor: color + '30' } : undefined}
      >
        <User className="h-4 w-4" style={color ? { color } : undefined} />
      </div>

      {/* Content */}
      <div
        className="max-w-[80%] rounded-lg px-4 py-2 bg-muted"
        style={color ? { borderLeft: `3px solid ${color}` } : undefined}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium" style={color ? { color } : undefined}>
            {displayName || slugToTitle(personaName)}
          </span>
          <span className="text-xs text-muted-foreground animate-pulse">
            typing...
          </span>
        </div>

        {/* Streaming content with cursor */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
          <span className="animate-pulse">▋</span>
        </div>
      </div>
    </div>
  );
}
