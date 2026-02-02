import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout/AppLayout';
import { LeftSidebar } from '@/components/layout/LeftSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { ChatArea } from '@/components/chat/ChatArea';
import { SettingsModal } from '@/components/modals/SettingsModal';
import { NewSessionModal } from '@/components/modals/NewSessionModal';
import { VoteResultsModal } from '@/components/modals/VoteResultsModal';
import { useStore } from '@/store';
import { personasApi, sessionsApi } from '@/lib/api';
import { wsClient } from '@/lib/websocket';
import type { WSEvent } from '@/types';

const SESSION_STORAGE_KEY = 'multi-agent-collab-session-id';

function App() {
  const {
    currentSession,
    setCurrentSession,
    setMessages,
    addMessage,
    startStreaming,
    appendStreamingChunk,
    completeStreaming,
    setPersonaThinking,
    updateTokenUsage,
    updateSessionPhase,
    updateSessionStatus,
    setDiscussionActive,
    setOrchestratorStatus,
    updateOrchestratorTokenUsage,
    setActiveVote,
    // Poll state
    activePoll,
    startPoll,
    addPollSynthesis,
    setPollPhase,
    addPollVote,
    setPollResults,
  } = useStore();

  // Prefetch personas count
  useQuery({
    queryKey: ['personas', 'count'],
    queryFn: personasApi.getCount,
  });

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
    if (savedSessionId && !currentSession) {
      const sessionId = parseInt(savedSessionId, 10);
      if (!isNaN(sessionId)) {
        sessionsApi.get(sessionId)
          .then((session) => {
            setCurrentSession(session);
            // Load messages for the session
            sessionsApi.getMessages(sessionId).then(setMessages).catch(console.error);
          })
          .catch((e) => {
            console.error('Failed to restore session:', e);
            localStorage.removeItem(SESSION_STORAGE_KEY);
          });
      }
    }
  }, []);

  // Save session ID to localStorage when it changes
  useEffect(() => {
    if (currentSession) {
      localStorage.setItem(SESSION_STORAGE_KEY, currentSession.id.toString());
    }
  }, [currentSession?.id]);

  // WebSocket event handling
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      switch (event.type) {
        case 'connected':
          console.log('Connected to session');
          break;

        case 'user_message':
          addMessage({
            id: Date.now(),
            role: 'user',
            content: event.data.content as string,
            turn_number: event.data.turn_number as number,
            metadata: {},
            created_at: event.timestamp,
          });
          break;

        case 'persona_thinking':
          setPersonaThinking(event.data.persona_name as string, true);
          startStreaming(event.data.persona_name as string);
          break;

        case 'persona_chunk':
          appendStreamingChunk(
            event.data.persona_name as string,
            event.data.chunk as string
          );
          break;

        case 'persona_done':
          setPersonaThinking(event.data.persona_name as string, false);
          completeStreaming(
            event.data.persona_name as string,
            event.data.content as string
          );
          addMessage({
            id: Date.now(),
            persona_name: event.data.persona_name as string,
            role: 'assistant',
            content: event.data.content as string,
            turn_number: (event.data.turn_number as number) || 1,
            round_number: (event.data.round_number as number) || 1,
            metadata: {},
            created_at: event.timestamp,
          });
          updateTokenUsage(event.data.persona_name as string, {
            input_tokens: event.data.input_tokens as number,
            output_tokens: event.data.output_tokens as number,
            total_tokens:
              (event.data.input_tokens as number) + (event.data.output_tokens as number),
            cost: 0,
          });
          break;

        case 'phase_change':
          updateSessionPhase(event.data.new_phase as any);
          break;

        case 'session_update':
          // Update session status from server
          if (event.data.status) {
            updateSessionStatus(event.data.status as string);
          }
          break;

        case 'token_update':
          // Additional token updates
          break;

        case 'orchestrator_status':
          setOrchestratorStatus({
            status: event.data.status as string,
            persona_name: event.data.persona_name as string | undefined,
            round_number: event.data.round_number as number | undefined,
            details: event.data.details as string | undefined,
            timestamp: event.timestamp,
            input_tokens: event.data.input_tokens as number | undefined,
            output_tokens: event.data.output_tokens as number | undefined,
            cache_read_tokens: event.data.cache_read_tokens as number | undefined,
            cache_creation_tokens: event.data.cache_creation_tokens as number | undefined,
          });
          // Update cumulative orchestrator token usage
          if (event.data.input_tokens || event.data.output_tokens || event.data.cache_read_tokens || event.data.cache_creation_tokens) {
            updateOrchestratorTokenUsage({
              input_tokens: event.data.input_tokens as number | undefined,
              output_tokens: event.data.output_tokens as number | undefined,
              cache_read_tokens: event.data.cache_read_tokens as number | undefined,
              cache_creation_tokens: event.data.cache_creation_tokens as number | undefined,
            });
          }
          break;

        case 'vote_request':
          // Vote started - add to chat
          addMessage({
            id: Date.now(),
            role: 'system',
            content: `📊 **Vote Requested**\n\n"${event.data.proposal}"`,
            turn_number: 0,
            metadata: { type: 'vote_request', proposal_id: event.data.proposal_id },
            created_at: event.timestamp,
          });
          break;

        case 'vote_received':
          // Individual vote received - could add to chat if desired
          console.log('Vote received:', event.data.persona_name, event.data.vote);
          break;

        case 'vote_complete': {
          // Check if this is a poll completion
          if (event.data.type === 'poll_complete') {
            const pollResults = event.data.poll_results as {
              simple_majority: { winner: string; winner_approval: number; breakdown: Record<string, { agrees: number; disagrees: number; abstains: number; approval_rate: number }> };
              caucus: Array<{ pattern: string; members: string[]; count: number }>;
              ranked_choice: { winner: string; rankings: Array<{ rank: number; option: string; score: number }> };
            };

            setPollResults({
              simple_majority: pollResults.simple_majority,
              ranked_choice: pollResults.ranked_choice,
              caucus: pollResults.caucus,
            });

            // Build exciting final results message
            const resultsLines = [
              '🎉 **POLL COMPLETE - FINAL RESULTS**',
              '',
              `📋 **Question:** "${event.data.question}"`,
              '',
              '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
              '',
              '🏆 **SIMPLE MAJORITY WINNER:**',
              `   **${pollResults.simple_majority.winner}**`,
              `   (${pollResults.simple_majority.winner_approval}% approval)`,
              '',
              '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
              '',
              '🎯 **RANKED CHOICE WINNER:**',
              `   **${pollResults.ranked_choice.winner}**`,
              '',
              '📊 **Full Rankings:**',
              ...pollResults.ranked_choice.rankings.map(r =>
                `   ${r.rank}. ${r.option} (${r.score.toFixed(1)} pts)`
              ),
              '',
              '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
              '',
              '🏛️ **CAUCUS BREAKDOWN:**',
              ...pollResults.caucus.map(c =>
                `   • ${c.count} personas: ${c.members.slice(0, 3).join(', ')}${c.members.length > 3 ? ` +${c.members.length - 3} more` : ''}`
              ),
              '',
              '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
              '',
              '✅ **CONSENSUS ANALYSIS:**',
              `   ${pollResults.simple_majority.winner === pollResults.ranked_choice.winner
                ? '🟢 Both methods agree - strong consensus!'
                : '🟡 Methods differ - topic may need more discussion'}`,
            ];

            addMessage({
              id: Date.now(),
              role: 'system',
              content: resultsLines.join('\n'),
              turn_number: 0,
              metadata: { type: 'poll_complete', poll_id: event.data.poll_id },
              created_at: event.timestamp,
            });
          } else {
            // Regular vote completion (non-poll)
            const voteData = {
              proposal: event.data.proposal as string,
              proposal_id: event.data.proposal_id as string,
              consensus_reached: event.data.consensus_reached as boolean,
              agreement_score: event.data.agreement_score as number,
              majority_vote: event.data.majority_vote as string | null,
              votes: event.data.votes as { agree: number; disagree: number; abstain: number },
              dissenting_personas: event.data.dissenting_personas as string[],
              vote_details: event.data.vote_details as Array<{
                persona: string;
                vote: string;
                confidence: number;
                reasoning: string;
              }>,
            };

            // Build vote results message
            const resultsLines = [
              `📊 **Vote Results**: "${voteData.proposal}"`,
              '',
              `**Consensus**: ${voteData.consensus_reached ? '✅ Reached' : '⚠️ Not Reached'} (${Math.round(voteData.agreement_score * 100)}% agreement)`,
              '',
              `**Votes**: ✅ ${voteData.votes.agree} Agree | ⏸️ ${voteData.votes.abstain} Abstain | ❌ ${voteData.votes.disagree} Disagree`,
              '',
              '**Individual Votes**:',
              ...voteData.vote_details.map(v =>
                `- **${v.persona}**: ${v.vote.toUpperCase()} (${Math.round(v.confidence * 100)}% confidence)${v.reasoning ? ` - "${v.reasoning}"` : ''}`
              ),
            ];

            addMessage({
              id: Date.now(),
              role: 'system',
              content: resultsLines.join('\n'),
              turn_number: 0,
              metadata: { type: 'vote_complete', ...voteData },
              created_at: event.timestamp,
            });

            setActiveVote(voteData);
          }
          break;
        }

        case 'error':
          console.error('WebSocket error:', event.data.message);
          break;

        // === POLL MODE: Live Election-Style Events ===
        case 'system_message': {
          const msgType = event.data.type as string;

          if (msgType === 'poll_started') {
            // New poll started!
            startPoll(event.data.poll_id as string, event.data.question as string);
            addMessage({
              id: Date.now(),
              role: 'system',
              content: `🗳️ **POLL STARTED**\n\n**Question:** "${event.data.question}"\n\n📝 Synthesis Phase: Personas are now proposing solutions...`,
              turn_number: 0,
              metadata: { type: 'poll_started', poll_id: event.data.poll_id },
              created_at: event.timestamp,
            });
          }

          else if (msgType === 'poll_synthesis') {
            // A persona submitted their synthesis!
            const personaName = event.data.persona_name as string;
            const optionsCount = event.data.options_count as number;
            const allSubmitted = event.data.all_submitted as boolean;

            addPollSynthesis({
              persona_name: personaName,
              framing: event.data.framing as string,
              options_count: optionsCount,
              timestamp: event.timestamp,
            });

            // Show exciting update
            const emoji = ['💡', '🎯', '✨', '🔥', '⚡'][Math.floor(Math.random() * 5)];
            addMessage({
              id: Date.now(),
              role: 'system',
              content: `${emoji} **${personaName}** proposed ${optionsCount} option${optionsCount > 1 ? 's' : ''}!${allSubmitted ? '\n\n✅ All personas have submitted - moving to voting!' : ''}`,
              turn_number: 0,
              metadata: { type: 'poll_synthesis', persona_name: personaName },
              created_at: event.timestamp,
            });
          }

          else if (msgType === 'poll_phase_change') {
            const newPhase = event.data.new_phase as string;
            const options = event.data.options as Array<{id: number; text: string}> | undefined;
            const top5 = event.data.top_5_options as Array<{id: number; text: string; score?: number}> | undefined;

            setPollPhase(
              newPhase as 'synthesis' | 'vote_round_1' | 'vote_round_2' | 'completed',
              options,
              top5
            );

            if (newPhase === 'vote_round_1') {
              const optionsList = options?.map((o, i) => `${i + 1}. ${o.text}`).join('\n') || '';
              addMessage({
                id: Date.now(),
                role: 'system',
                content: `📊 **VOTE ROUND 1 - RANKED CHOICE**\n\n🎯 ${options?.length || 0} options to rank:\n\n${optionsList}\n\n⏳ Waiting for all ${activePoll?.synthesis_entries?.length || '21'} personas to submit rankings...`,
                turn_number: 0,
                metadata: { type: 'poll_phase_change', phase: newPhase },
                created_at: event.timestamp,
              });
            }

            else if (newPhase === 'vote_round_2') {
              const top5List = top5?.map((o, i) => `${i + 1}. ${o.text} (Score: ${o.score?.toFixed(1) || '?'})`).join('\n') || '';
              addMessage({
                id: Date.now(),
                role: 'system',
                content: `🏆 **FINAL ROUND - TOP 5 OPTIONS**\n\n🎯 These options advanced:\n\n${top5List}\n\n🗳️ Final vote in progress...`,
                turn_number: 0,
                metadata: { type: 'poll_phase_change', phase: newPhase },
                created_at: event.timestamp,
              });
            }
          }

          else if (msgType === 'poll_vote_received') {
            // Live vote coming in!
            const personaName = event.data.persona_name as string;
            const round = event.data.vote_round as number;

            addPollVote(round as 1 | 2, personaName);

            // Count votes for progress
            const voteCount = round === 1
              ? (activePoll?.round_1_votes?.length || 0) + 1
              : (activePoll?.round_2_votes?.length || 0) + 1;
            const totalPersonas = activePoll?.synthesis_entries?.length || 21;
            const progress = Math.round((voteCount / totalPersonas) * 100);

            // Progress bar visualization
            const filled = Math.round(progress / 5);
            const progressBar = '█'.repeat(filled) + '░'.repeat(20 - filled);

            addMessage({
              id: Date.now(),
              role: 'system',
              content: `🗳️ **${personaName}** voted! [${voteCount}/${totalPersonas}]\n\n\`${progressBar}\` ${progress}%`,
              turn_number: 0,
              metadata: { type: 'poll_vote', persona_name: personaName, round },
              created_at: event.timestamp,
            });
          }
          break;
        }
      }
    };

    const unsubscribe = wsClient.on('*', handleEvent);
    return () => unsubscribe();
  }, []);

  // Connect to session WebSocket when session changes
  useEffect(() => {
    if (currentSession) {
      wsClient.connect(currentSession.id).catch(console.error);
      setDiscussionActive(currentSession.status === 'active');
    } else {
      wsClient.disconnect();
      setMessages([]);
    }

    return () => {
      wsClient.disconnect();
    };
  }, [currentSession?.id]);

  return (
    <div className="h-screen w-screen overflow-hidden bg-background">
      <AppLayout
        leftSidebar={<LeftSidebar />}
        rightSidebar={<RightSidebar />}
        main={<ChatArea />}
      />
      <SettingsModal />
      <NewSessionModal />
      <VoteResultsModal />
    </div>
  );
}

export default App;
