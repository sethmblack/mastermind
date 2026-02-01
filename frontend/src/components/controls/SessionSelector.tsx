import { useQuery } from '@tanstack/react-query';
import { useStore } from '@/store';
import { sessionsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RefreshCw, Trash2 } from 'lucide-react';
import type { SessionSummary } from '@/types';

export function SessionSelector() {
  const { currentSession, setCurrentSession, setMessages } = useStore();

  const { data: sessions, isLoading, refetch } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list(undefined, 20, 0),
  });

  const handleSessionChange = async (sessionId: string) => {
    if (sessionId === 'new') {
      setCurrentSession(null);
      setMessages([]);
      return;
    }

    const id = parseInt(sessionId, 10);
    try {
      const session = await sessionsApi.get(id);
      setCurrentSession(session);
      const messages = await sessionsApi.getMessages(id);
      setMessages(messages);
    } catch (e) {
      console.error('Failed to load session:', e);
    }
  };

  const handleDeleteSession = async () => {
    if (!currentSession) return;
    if (!confirm(`Delete session "${currentSession.name}"?`)) return;

    try {
      await sessionsApi.delete(currentSession.id);
      setCurrentSession(null);
      setMessages([]);
      refetch();
    } catch (e) {
      console.error('Failed to delete session:', e);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Select
          value={currentSession?.id?.toString() || 'new'}
          onValueChange={handleSessionChange}
        >
          <SelectTrigger className="flex-1">
            <SelectValue placeholder="Select a session..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="new">+ New Session</SelectItem>
            {sessions?.map((session: SessionSummary) => (
              <SelectItem key={session.id} value={session.id.toString()}>
                {session.name} ({session.message_count} msgs)
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>

        {currentSession && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleDeleteSession}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>

      {currentSession && (
        <p className="text-xs text-muted-foreground">
          {currentSession.personas?.length || 0} personas · {currentSession.status}
        </p>
      )}
    </div>
  );
}
