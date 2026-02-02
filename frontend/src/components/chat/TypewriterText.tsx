import { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

interface TypewriterTextProps {
  content: string;
  speed?: number; // characters per second
  onComplete?: () => void;
  enabled?: boolean;
}

export function TypewriterText({
  content,
  speed = 80, // ~80 chars/sec = readable speed
  onComplete,
  enabled = true,
}: TypewriterTextProps) {
  const [displayedContent, setDisplayedContent] = useState(enabled ? '' : content);
  const [isComplete, setIsComplete] = useState(!enabled);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const indexRef = useRef(0);

  useEffect(() => {
    if (!enabled) {
      setDisplayedContent(content);
      setIsComplete(true);
      return;
    }

    // Reset when content changes
    indexRef.current = 0;
    setDisplayedContent('');
    setIsComplete(false);

    const msPerChar = 1000 / speed;

    intervalRef.current = setInterval(() => {
      if (indexRef.current < content.length) {
        // Add multiple characters at once for smoother rendering
        const charsToAdd = Math.min(3, content.length - indexRef.current);
        indexRef.current += charsToAdd;
        setDisplayedContent(content.slice(0, indexRef.current));
      } else {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        setIsComplete(true);
        onComplete?.();
      }
    }, msPerChar * 3); // Multiply by chars added per tick

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [content, speed, enabled, onComplete]);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown>{displayedContent}</ReactMarkdown>
      {!isComplete && <span className="animate-pulse">▋</span>}
    </div>
  );
}
