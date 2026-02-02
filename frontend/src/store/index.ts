import { create } from 'zustand';
import type {
  Session,
  Message,
  PersonaSummary,
  SessionPhase,
  TokenUsage,
} from '@/types';

interface StreamingMessage {
  persona_name: string;
  content: string;
  isComplete: boolean;
}

interface OrchestratorStatus {
  status: string;  // "checking", "generating", "submitting", "waiting", "complete", "idle"
  persona_name?: string;
  round_number?: number;
  details?: string;
  timestamp: string;
  // Token usage from Claude Code
  input_tokens?: number;
  output_tokens?: number;
  cache_read_tokens?: number;
  cache_creation_tokens?: number;
}

interface OrchestratorTokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  total_tokens: number;
}

interface VoteDetail {
  persona: string;
  vote: string;
  confidence: number;
  reasoning: string;
}

interface VoteResult {
  proposal: string;
  proposal_id: string;
  consensus_reached: boolean;
  agreement_score: number;
  majority_vote: string | null;
  votes: {
    agree: number;
    disagree: number;
    abstain: number;
  };
  dissenting_personas: string[];
  vote_details: VoteDetail[];
}

// Poll state for live election tracking
interface PollOption {
  id: number;
  text: string;
  proposed_by?: string;
  score?: number;
}

interface PollSynthesisEntry {
  persona_name: string;
  framing: string;
  options_count: number;
  timestamp: string;
}

interface PollVoteEntry {
  persona_name: string;
  voted_at: string;
}

interface LivePollState {
  poll_id: string;
  question: string;
  phase: 'synthesis' | 'vote_round_1' | 'vote_round_2' | 'completed';
  options: PollOption[];
  synthesis_entries: PollSynthesisEntry[];
  round_1_votes: PollVoteEntry[];
  round_2_votes: PollVoteEntry[];
  top_5_options?: PollOption[];
  final_results?: {
    simple_majority: { winner: string; winner_approval: number };
    ranked_choice: { winner: string };
    caucus: Array<{ pattern: string; members: string[]; count: number }>;
  };
}

interface AppState {
  // Session state
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;
  updateSessionPhase: (phase: SessionPhase) => void;
  updateSessionStatus: (status: string) => void;

  // Messages
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;

  // Track messages that should animate (typewriter effect)
  animatingMessageIds: Set<number>;
  markMessageAnimated: (messageId: number) => void;

  // Streaming state
  streamingMessages: Map<string, StreamingMessage>;
  startStreaming: (personaName: string) => void;
  appendStreamingChunk: (personaName: string, chunk: string) => void;
  completeStreaming: (personaName: string, fullContent: string) => void;

  // Active personas
  activePersonas: string[];
  setActivePersonas: (personas: string[]) => void;

  // Thinking state
  thinkingPersonas: Set<string>;
  setPersonaThinking: (personaName: string, isThinking: boolean) => void;

  // Token usage
  tokenUsage: Map<string, TokenUsage>;
  updateTokenUsage: (personaName: string, usage: TokenUsage) => void;
  totalTokenUsage: TokenUsage;

  // Discussion state
  isDiscussionActive: boolean;
  setDiscussionActive: (active: boolean) => void;

  // Selected personas for new session
  selectedPersonas: PersonaSummary[];
  addSelectedPersona: (persona: PersonaSummary) => void;
  removeSelectedPersona: (personaName: string) => void;
  clearSelectedPersonas: () => void;

  // Orchestrator status
  orchestratorStatus: OrchestratorStatus | null;
  setOrchestratorStatus: (status: OrchestratorStatus | null) => void;

  // Vote results
  activeVote: VoteResult | null;
  setActiveVote: (vote: VoteResult | null) => void;

  // Live poll state for election-day excitement
  activePoll: LivePollState | null;
  startPoll: (poll_id: string, question: string) => void;
  addPollSynthesis: (entry: PollSynthesisEntry) => void;
  setPollPhase: (phase: LivePollState['phase'], options?: PollOption[], top5?: PollOption[]) => void;
  addPollVote: (round: 1 | 2, persona_name: string) => void;
  setPollResults: (results: LivePollState['final_results']) => void;
  clearPoll: () => void;

  // Orchestrator token usage (cumulative)
  orchestratorTokenUsage: OrchestratorTokenUsage;
  updateOrchestratorTokenUsage: (tokens: Partial<OrchestratorTokenUsage>) => void;

  // UI state
  leftSidebarOpen: boolean;
  rightSidebarOpen: boolean;
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;

  // Reset
  reset: () => void;
}

const initialTokenUsage: TokenUsage = {
  input_tokens: 0,
  output_tokens: 0,
  total_tokens: 0,
  cost: 0,
};

export const useStore = create<AppState>((set) => ({
  // Session state
  currentSession: null,
  setCurrentSession: (session) => set({ currentSession: session }),
  updateSessionPhase: (phase) =>
    set((state) => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, phase }
        : null,
    })),
  updateSessionStatus: (status: string) =>
    set((state) => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, status: status as 'active' | 'paused' | 'completed' | 'archived' }
        : null,
      isDiscussionActive: status === 'active',
    })),

  // Messages
  messages: [],
  setMessages: (messages) => set({ messages, animatingMessageIds: new Set() }),
  addMessage: (message) =>
    set((state) => {
      // Prevent duplicate messages based on persona + round + content hash
      const isDuplicate = state.messages.some((m) => {
        // Check by database ID if available
        if (message.id && m.id === message.id) return true;
        // Check by persona + round + content start (for WebSocket messages without real IDs)
        if (
          m.persona_name === message.persona_name &&
          m.round_number === message.round_number &&
          m.content?.substring(0, 50) === message.content?.substring(0, 50)
        ) {
          return true;
        }
        return false;
      });

      if (isDuplicate) {
        console.log('Skipping duplicate message:', message.persona_name, message.round_number);
        return state;
      }

      const newAnimatingIds = new Set(state.animatingMessageIds);
      if (message.id) {
        newAnimatingIds.add(message.id);
      }
      return {
        messages: [...state.messages, message],
        animatingMessageIds: newAnimatingIds,
      };
    }),

  // Track messages that should animate (typewriter effect)
  animatingMessageIds: new Set(),
  markMessageAnimated: (messageId) =>
    set((state) => {
      const newSet = new Set(state.animatingMessageIds);
      newSet.delete(messageId);
      return { animatingMessageIds: newSet };
    }),

  // Streaming state
  streamingMessages: new Map(),
  startStreaming: (personaName) =>
    set((state) => {
      const newMap = new Map(state.streamingMessages);
      newMap.set(personaName, { persona_name: personaName, content: '', isComplete: false });
      return { streamingMessages: newMap };
    }),
  appendStreamingChunk: (personaName, chunk) =>
    set((state) => {
      const newMap = new Map(state.streamingMessages);
      const current = newMap.get(personaName);
      if (current) {
        newMap.set(personaName, { ...current, content: current.content + chunk });
      }
      return { streamingMessages: newMap };
    }),
  completeStreaming: (personaName, _fullContent) =>
    set((state) => {
      const newMap = new Map(state.streamingMessages);
      newMap.delete(personaName);
      return { streamingMessages: newMap };
    }),

  // Active personas
  activePersonas: [],
  setActivePersonas: (personas) => set({ activePersonas: personas }),

  // Thinking state
  thinkingPersonas: new Set(),
  setPersonaThinking: (personaName, isThinking) =>
    set((state) => {
      const newSet = new Set(state.thinkingPersonas);
      if (isThinking) {
        newSet.add(personaName);
      } else {
        newSet.delete(personaName);
      }
      return { thinkingPersonas: newSet };
    }),

  // Token usage
  tokenUsage: new Map(),
  updateTokenUsage: (personaName, usage) =>
    set((state) => {
      const newMap = new Map(state.tokenUsage);
      const current = newMap.get(personaName) || { ...initialTokenUsage };
      newMap.set(personaName, {
        input_tokens: current.input_tokens + usage.input_tokens,
        output_tokens: current.output_tokens + usage.output_tokens,
        total_tokens: current.total_tokens + usage.total_tokens,
        cost: current.cost + usage.cost,
      });

      // Calculate total
      let totalInput = 0;
      let totalOutput = 0;
      let totalCost = 0;
      newMap.forEach((u) => {
        totalInput += u.input_tokens;
        totalOutput += u.output_tokens;
        totalCost += u.cost;
      });

      return {
        tokenUsage: newMap,
        totalTokenUsage: {
          input_tokens: totalInput,
          output_tokens: totalOutput,
          total_tokens: totalInput + totalOutput,
          cost: totalCost,
        },
      };
    }),
  totalTokenUsage: { ...initialTokenUsage },

  // Discussion state
  isDiscussionActive: false,
  setDiscussionActive: (active) => set({ isDiscussionActive: active }),

  // Selected personas
  selectedPersonas: [],
  addSelectedPersona: (persona) =>
    set((state) => {
      if (state.selectedPersonas.length >= 5) return state;
      if (state.selectedPersonas.some((p) => p.name === persona.name)) return state;
      return { selectedPersonas: [...state.selectedPersonas, persona] };
    }),
  removeSelectedPersona: (personaName) =>
    set((state) => ({
      selectedPersonas: state.selectedPersonas.filter((p) => p.name !== personaName),
    })),
  clearSelectedPersonas: () => set({ selectedPersonas: [] }),

  // Orchestrator status
  orchestratorStatus: null,
  setOrchestratorStatus: (status) => set({ orchestratorStatus: status }),

  // Vote results
  activeVote: null,
  setActiveVote: (vote) => set({ activeVote: vote }),

  // Live poll state
  activePoll: null,
  startPoll: (poll_id, question) => set({
    activePoll: {
      poll_id,
      question,
      phase: 'synthesis',
      options: [],
      synthesis_entries: [],
      round_1_votes: [],
      round_2_votes: [],
    }
  }),
  addPollSynthesis: (entry) => set((state) => {
    if (!state.activePoll) return state;
    return {
      activePoll: {
        ...state.activePoll,
        synthesis_entries: [...state.activePoll.synthesis_entries, entry],
      }
    };
  }),
  setPollPhase: (phase, options, top5) => set((state) => {
    if (!state.activePoll) return state;
    return {
      activePoll: {
        ...state.activePoll,
        phase,
        options: options || state.activePoll.options,
        top_5_options: top5 || state.activePoll.top_5_options,
      }
    };
  }),
  addPollVote: (round, persona_name) => set((state) => {
    if (!state.activePoll) return state;
    const entry = { persona_name, voted_at: new Date().toISOString() };
    if (round === 1) {
      return {
        activePoll: {
          ...state.activePoll,
          round_1_votes: [...state.activePoll.round_1_votes, entry],
        }
      };
    } else {
      return {
        activePoll: {
          ...state.activePoll,
          round_2_votes: [...state.activePoll.round_2_votes, entry],
        }
      };
    }
  }),
  setPollResults: (results) => set((state) => {
    if (!state.activePoll) return state;
    return {
      activePoll: {
        ...state.activePoll,
        phase: 'completed',
        final_results: results,
      }
    };
  }),
  clearPoll: () => set({ activePoll: null }),

  // Orchestrator token usage (cumulative from Claude Code)
  orchestratorTokenUsage: {
    input_tokens: 0,
    output_tokens: 0,
    cache_read_tokens: 0,
    cache_creation_tokens: 0,
    total_tokens: 0,
  },
  updateOrchestratorTokenUsage: (tokens) =>
    set(() => {
      // Set cumulative values directly (not adding)
      const updated = {
        input_tokens: tokens.input_tokens || 0,
        output_tokens: tokens.output_tokens || 0,
        cache_read_tokens: tokens.cache_read_tokens || 0,
        cache_creation_tokens: tokens.cache_creation_tokens || 0,
        total_tokens: 0,
      };
      updated.total_tokens = updated.input_tokens + updated.output_tokens + updated.cache_read_tokens + updated.cache_creation_tokens;
      return { orchestratorTokenUsage: updated };
    }),

  // UI state
  leftSidebarOpen: true,
  rightSidebarOpen: true,
  toggleLeftSidebar: () => set((state) => ({ leftSidebarOpen: !state.leftSidebarOpen })),
  toggleRightSidebar: () => set((state) => ({ rightSidebarOpen: !state.rightSidebarOpen })),
  settingsOpen: false,
  setSettingsOpen: (open) => set({ settingsOpen: open }),

  // Reset
  reset: () =>
    set({
      currentSession: null,
      messages: [],
      animatingMessageIds: new Set(),
      streamingMessages: new Map(),
      activePersonas: [],
      thinkingPersonas: new Set(),
      tokenUsage: new Map(),
      totalTokenUsage: { ...initialTokenUsage },
      isDiscussionActive: false,
      selectedPersonas: [],
      orchestratorStatus: null,
      activeVote: null,
      activePoll: null,
      orchestratorTokenUsage: {
        input_tokens: 0,
        output_tokens: 0,
        cache_read_tokens: 0,
        cache_creation_tokens: 0,
        total_tokens: 0,
      },
    }),
}));
