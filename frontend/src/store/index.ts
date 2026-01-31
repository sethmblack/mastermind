import { create } from 'zustand';
import type {
  Session,
  SessionPersona,
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

interface AppState {
  // Session state
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;
  updateSessionPhase: (phase: SessionPhase) => void;

  // Messages
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;

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

export const useStore = create<AppState>((set, get) => ({
  // Session state
  currentSession: null,
  setCurrentSession: (session) => set({ currentSession: session }),
  updateSessionPhase: (phase) =>
    set((state) => ({
      currentSession: state.currentSession
        ? { ...state.currentSession, phase }
        : null,
    })),

  // Messages
  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

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
  completeStreaming: (personaName, fullContent) =>
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
      streamingMessages: new Map(),
      activePersonas: [],
      thinkingPersonas: new Set(),
      tokenUsage: new Map(),
      totalTokenUsage: { ...initialTokenUsage },
      isDiscussionActive: false,
      selectedPersonas: [],
    }),
}));
