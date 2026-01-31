import { cn, formatRelativeTime, slugToTitle } from '@/lib/utils';
import type { Message } from '@/types';
import { User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  message: Message;
  color?: string;
  displayName?: string;
}

export function MessageBubble({ message, color, displayName }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="text-center text-xs text-muted-foreground py-2">
        {message.content}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isUser ? 'bg-primary' : 'bg-muted'
        )}
        style={!isUser && color ? { backgroundColor: color + '30' } : undefined}
      >
        <User
          className="h-4 w-4"
          style={!isUser && color ? { color } : undefined}
        />
      </div>

      {/* Content */}
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
        style={
          !isUser && color
            ? { borderLeft: `3px solid ${color}` }
            : undefined
        }
      >
        {/* Header */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-sm font-medium"
              style={color ? { color } : undefined}
            >
              {displayName || slugToTitle(message.persona_name || 'Assistant')}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(message.created_at)}
            </span>
          </div>
        )}

        {/* Message content */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
