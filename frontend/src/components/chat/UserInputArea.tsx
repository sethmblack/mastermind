import { useState, useRef, useEffect } from 'react';
import { useStore } from '@/store';
import { wsClient } from '@/lib/websocket';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Square } from 'lucide-react';

export function UserInputArea() {
  const [message, setMessage] = useState('');
  const { thinkingPersonas } = useStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isThinking = thinkingPersonas.size > 0;

  const handleSend = () => {
    if (!message.trim() || isThinking) return;

    wsClient.sendUserMessage(message.trim());
    setMessage('');

    // Focus back on textarea
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStop = () => {
    wsClient.stopDiscussion();
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [message]);

  return (
    <div className="border-t border-border p-4 bg-card/50">
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
            className="resize-none min-h-[44px] max-h-[200px]"
            rows={1}
            disabled={isThinking}
          />
          {isThinking ? (
            <Button
              variant="destructive"
              size="icon"
              onClick={handleStop}
              className="h-11 w-11 flex-shrink-0"
            >
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!message.trim()}
              className="h-11 w-11 flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Status bar */}
        <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
          <span>
            {wsClient.isConnected ? (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                Disconnected
              </span>
            )}
          </span>
          <span>{message.length} characters</span>
        </div>
      </div>
    </div>
  );
}
