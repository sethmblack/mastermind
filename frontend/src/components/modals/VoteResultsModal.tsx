import { useStore } from '@/store';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle, XCircle, MinusCircle, Vote, Users, Trophy, BarChart3 } from 'lucide-react';

interface PollResults {
  simple_majority: {
    winner: string;
    votes: number;
    total_voters: number;
    percentage: number;
    breakdown: Record<string, number>;
  };
  caucus: Record<string, {
    members: Array<{ persona: string; confidence: number }>;
    count: number;
    percentage: number;
  }>;
  ranked_choice: {
    winner: string;
    rounds: Array<{
      counts: Record<string, number>;
      total: number;
      eliminated?: string;
      winner?: string;
    }>;
    total_rounds: number;
  };
}

export function VoteResultsModal() {
  const { activeVote, setActiveVote, currentSession } = useStore();

  if (!activeVote) return null;

  const personaColors: Record<string, string> = {};
  currentSession?.personas.forEach((p) => {
    personaColors[p.persona_name] = p.color || '#888';
  });

  const isPollMode = !!(activeVote as any).poll_results;
  const pollResults = (activeVote as any).poll_results as PollResults | undefined;

  const getVoteIcon = (vote: string) => {
    switch (vote.toLowerCase()) {
      case 'agree':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'disagree':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <MinusCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getVoteColor = (vote: string) => {
    switch (vote.toLowerCase()) {
      case 'agree':
        return 'bg-green-500/10 text-green-500 border-green-500/30';
      case 'disagree':
        return 'bg-red-500/10 text-red-500 border-red-500/30';
      default:
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30';
    }
  };

  const getDisplayName = (personaName: string) => {
    return currentSession?.personas.find(p => p.persona_name === personaName)?.display_name || personaName;
  };

  return (
    <Dialog open={!!activeVote} onOpenChange={(open) => !open && setActiveVote(null)}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Vote className="h-5 w-5" />
            {isPollMode ? 'Poll Results' : 'Vote Results'}
          </DialogTitle>
          <DialogDescription className="text-base font-medium">
            "{activeVote.proposal}"
          </DialogDescription>
        </DialogHeader>

        {isPollMode && pollResults ? (
          /* Poll Mode Results with Tabs */
          <Tabs defaultValue="majority" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="majority" className="flex items-center gap-1">
                <BarChart3 className="h-3 w-3" />
                Simple Majority
              </TabsTrigger>
              <TabsTrigger value="caucus" className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                Caucus
              </TabsTrigger>
              <TabsTrigger value="ranked" className="flex items-center gap-1">
                <Trophy className="h-3 w-3" />
                Ranked Choice
              </TabsTrigger>
            </TabsList>

            {/* Simple Majority Tab */}
            <TabsContent value="majority" className="space-y-4">
              <div className="p-4 rounded-lg bg-muted text-center">
                <div className="text-sm text-muted-foreground mb-1">Winner</div>
                <div className="text-2xl font-bold text-primary">
                  {pollResults.simple_majority.winner?.toUpperCase() || 'Tie'}
                </div>
                <div className="text-sm text-muted-foreground">
                  {pollResults.simple_majority.votes} of {pollResults.simple_majority.total_voters} votes ({pollResults.simple_majority.percentage}%)
                </div>
              </div>
              <div className="space-y-2">
                {Object.entries(pollResults.simple_majority.breakdown).map(([option, count]) => (
                  <div key={option} className="flex items-center gap-2">
                    <span className="w-24 text-sm font-medium">{option}</span>
                    <Progress value={(count / pollResults.simple_majority.total_voters) * 100} className="flex-1" />
                    <span className="w-12 text-sm text-right">{count}</span>
                  </div>
                ))}
              </div>
            </TabsContent>

            {/* Caucus Tab */}
            <TabsContent value="caucus" className="space-y-4">
              {Object.entries(pollResults.caucus).map(([option, data]) => (
                <div key={option} className="p-3 rounded-lg border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{option.toUpperCase()}</span>
                    <Badge variant="secondary">{data.count} members ({data.percentage}%)</Badge>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {data.members.map((member) => (
                      <Badge
                        key={member.persona}
                        variant="outline"
                        className="text-xs"
                        style={{ borderColor: personaColors[member.persona] + '50', color: personaColors[member.persona] }}
                      >
                        {getDisplayName(member.persona)}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </TabsContent>

            {/* Ranked Choice Tab */}
            <TabsContent value="ranked" className="space-y-4">
              <div className="p-4 rounded-lg bg-muted text-center">
                <div className="text-sm text-muted-foreground mb-1">Winner (after {pollResults.ranked_choice.total_rounds} rounds)</div>
                <div className="text-2xl font-bold text-primary">
                  {pollResults.ranked_choice.winner?.toUpperCase() || 'No Winner'}
                </div>
              </div>
              <div className="space-y-3">
                {pollResults.ranked_choice.rounds.map((round, idx) => (
                  <div key={idx} className="p-3 rounded-lg border bg-card">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">Round {idx + 1}</span>
                      {round.eliminated && (
                        <Badge variant="destructive" className="text-xs">
                          Eliminated: {round.eliminated}
                        </Badge>
                      )}
                      {round.winner && (
                        <Badge variant="default" className="text-xs bg-green-500">
                          Winner: {round.winner}
                        </Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(round.counts).map(([option, count]) => (
                        <div key={option} className="flex justify-between">
                          <span>{option}</span>
                          <span className="font-medium">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        ) : (
          /* Standard Vote Results */
          <>
            {/* Consensus indicator */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted">
              <div>
                <div className="text-sm text-muted-foreground">Consensus</div>
                <div className="text-lg font-semibold">
                  {activeVote.consensus_reached ? (
                    <span className="text-green-500">Reached</span>
                  ) : (
                    <span className="text-yellow-500">Not Reached</span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Agreement</div>
                <div className="text-lg font-semibold">
                  {Math.round(activeVote.agreement_score * 100)}%
                </div>
              </div>
            </div>

            {/* Vote counts */}
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 rounded-lg bg-green-500/10">
                <div className="text-2xl font-bold text-green-500">
                  {activeVote.votes.agree}
                </div>
                <div className="text-xs text-muted-foreground">Agree</div>
              </div>
              <div className="p-2 rounded-lg bg-yellow-500/10">
                <div className="text-2xl font-bold text-yellow-500">
                  {activeVote.votes.abstain}
                </div>
                <div className="text-xs text-muted-foreground">Abstain</div>
              </div>
              <div className="p-2 rounded-lg bg-red-500/10">
                <div className="text-2xl font-bold text-red-500">
                  {activeVote.votes.disagree}
                </div>
                <div className="text-xs text-muted-foreground">Disagree</div>
              </div>
            </div>
          </>
        )}

        {/* Individual votes (shown for both modes) */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          <div className="text-sm font-medium text-muted-foreground mb-2">Individual Votes</div>
          {activeVote.vote_details.map((detail) => (
            <div
              key={detail.persona}
              className="p-3 rounded-lg border bg-card"
              style={{ borderColor: personaColors[detail.persona] + '50' }}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className="font-medium text-sm"
                  style={{ color: personaColors[detail.persona] }}
                >
                  {getDisplayName(detail.persona)}
                </span>
                <Badge variant="outline" className={getVoteColor(detail.vote)}>
                  {getVoteIcon(detail.vote)}
                  <span className="ml-1">{detail.vote}</span>
                </Badge>
              </div>
              {detail.reasoning && (
                <p className="text-xs text-muted-foreground mt-1">
                  {detail.reasoning}
                </p>
              )}
              <div className="flex items-center gap-1 mt-1">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <Progress value={detail.confidence * 100} className="h-1 flex-1" />
                <span className="text-xs text-muted-foreground">
                  {Math.round(detail.confidence * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>

        <Button variant="outline" onClick={() => setActiveVote(null)}>
          Close
        </Button>
      </DialogContent>
    </Dialog>
  );
}
