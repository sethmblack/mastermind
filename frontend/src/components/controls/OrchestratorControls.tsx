import { useStore } from '@/store';
import { sessionsApi } from '@/lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { turnModeLabels } from '@/lib/utils';
import { wsClient } from '@/lib/websocket';
import type { TurnMode } from '@/types';
import { Vote, Swords } from 'lucide-react';
import { useState } from 'react';

export function OrchestratorControls() {
  const { currentSession, setCurrentSession } = useStore();
  const [voteProposal, setVoteProposal] = useState('');

  if (!currentSession) return null;

  const handleTurnModeChange = async (mode: TurnMode) => {
    const updated = await sessionsApi.update(currentSession.id, {
      turn_mode: mode,
    });
    setCurrentSession(updated);
  };

  const handleRequestVote = () => {
    if (voteProposal.trim()) {
      wsClient.requestVote(voteProposal.trim());
      setVoteProposal('');
    }
  };

  return (
    <div className="space-y-4">
      {/* Turn Mode */}
      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Turn Mode</label>
        <Select
          value={currentSession.turn_mode}
          onValueChange={(value) => handleTurnModeChange(value as TurnMode)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(turnModeLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {currentSession.turn_mode === 'round_robin' &&
            'Personas take turns speaking in order'}
          {currentSession.turn_mode === 'moderator' &&
            'A moderator controls who speaks'}
          {currentSession.turn_mode === 'free_form' &&
            'Any persona can respond at any time'}
          {currentSession.turn_mode === 'interrupt' &&
            'Personas can interrupt with urgent input'}
          {currentSession.turn_mode === 'parallel' &&
            'All personas respond simultaneously'}
        </p>
      </div>

      {/* Request Vote */}
      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Request Vote</label>
        <div className="flex gap-2">
          <Input
            value={voteProposal}
            onChange={(e) => setVoteProposal(e.target.value)}
            placeholder="Enter proposal..."
            className="flex-1"
          />
          <Button
            size="icon"
            variant="outline"
            onClick={handleRequestVote}
            disabled={!voteProposal.trim()}
          >
            <Vote className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Quick Actions</label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => wsClient.requestVote('Should we proceed with the current approach?')}
          >
            <Vote className="h-3 w-3 mr-1" />
            Consensus Check
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => wsClient.send({
              type: 'user_message',
              data: { content: 'Please challenge the current thinking and identify potential flaws.' }
            })}
          >
            <Swords className="h-3 w-3 mr-1" />
            Challenge
          </Button>
        </div>
      </div>
    </div>
  );
}
