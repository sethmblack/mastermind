import { slugToTitle } from '@/lib/utils';
import { User } from 'lucide-react';

interface TypingIndicatorProps {
  personaName: string;
  color?: string;
  displayName?: string;
}

export function TypingIndicator({
  personaName,
  color,
  displayName,
}: TypingIndicatorProps) {
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
        className="rounded-lg px-4 py-2 bg-muted"
        style={color ? { borderLeft: `3px solid ${color}` } : undefined}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium" style={color ? { color } : undefined}>
            {displayName || slugToTitle(personaName)}
          </span>
          <div className="typing-indicator flex gap-1">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}
