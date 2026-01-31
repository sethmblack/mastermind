import { useStore } from '@/store';
import { sessionsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { statusLabels } from '@/lib/utils';
import { Play, Pause, StopCircle, RotateCcw } from 'lucide-react';
import { wsClient } from '@/lib/websocket';
import { useState } from 'react';

export function SessionControls() {
  const { currentSession, isDiscussionActive, setCurrentSession } = useStore();
  const [isEditing, setIsEditing] = useState(false);
  const [problemStatement, setProblemStatement] = useState(
    currentSession?.problem_statement || ''
  );

  if (!currentSession) return null;

  const handleStartDiscussion = () => {
    wsClient.startDiscussion();
  };

  const handlePauseDiscussion = () => {
    wsClient.pauseDiscussion();
  };

  const handleResumeDiscussion = () => {
    wsClient.resumeDiscussion();
  };

  const handleStopDiscussion = () => {
    wsClient.stopDiscussion();
  };

  const handleUpdateProblem = async () => {
    if (currentSession) {
      const updated = await sessionsApi.update(currentSession.id, {
        problem_statement: problemStatement,
      });
      setCurrentSession(updated);
      setIsEditing(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Status */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Status</span>
        <Badge
          variant={currentSession.status === 'active' ? 'default' : 'secondary'}
        >
          {statusLabels[currentSession.status]}
        </Badge>
      </div>

      {/* Problem Statement */}
      <div className="space-y-2">
        <span className="text-sm text-muted-foreground">Problem Statement</span>
        {isEditing ? (
          <div className="space-y-2">
            <Textarea
              value={problemStatement}
              onChange={(e) => setProblemStatement(e.target.value)}
              placeholder="What problem should the personas discuss?"
              rows={3}
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleUpdateProblem}>
                Save
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setProblemStatement(currentSession.problem_statement || '');
                  setIsEditing(false);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div
            className="text-sm p-2 bg-muted rounded cursor-pointer hover:bg-muted/80"
            onClick={() => setIsEditing(true)}
          >
            {currentSession.problem_statement || (
              <span className="text-muted-foreground italic">
                Click to add problem statement...
              </span>
            )}
          </div>
        )}
      </div>

      {/* Discussion Controls */}
      <div className="flex gap-2">
        {!isDiscussionActive ? (
          <Button
            className="flex-1"
            onClick={handleStartDiscussion}
            disabled={currentSession.status === 'completed'}
          >
            <Play className="h-4 w-4 mr-2" />
            Start
          </Button>
        ) : (
          <>
            <Button
              variant="outline"
              className="flex-1"
              onClick={handlePauseDiscussion}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={handleStopDiscussion}
            >
              <StopCircle className="h-4 w-4 mr-2" />
              Stop
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
