// Session types
export type SessionPhase =
  | 'discovery'
  | 'ideation'
  | 'evaluation'
  | 'decision'
  | 'action'
  | 'synthesis';

export type SessionStatus = 'active' | 'paused' | 'completed' | 'archived';

export type TurnMode =
  | 'round_robin'
  | 'moderator'
  | 'free_form'
  | 'interrupt'
  | 'parallel';

export interface SessionConfig {
  require_citations: boolean;
  steelman_mode: boolean;
  devil_advocate: boolean;
  fact_check: boolean;
  assumption_surfacing: boolean;
  blind_spot_detection: boolean;
  time_box_minutes?: number;
  max_turns?: number;
  min_rounds: number;  // Minimum discussion rounds (default 3)
  max_rounds: number;  // Maximum discussion rounds (default 3)
  web_search_enabled: boolean;
  code_execution_enabled: boolean;
  mcp_mode: boolean;  // Use Claude Code to power responses
  poll_mode: boolean;  // Multi-phase poll mode (up to 21 personas)
}

export interface Session {
  id: number;
  name: string;
  problem_statement?: string;
  status: SessionStatus;
  phase: SessionPhase;
  turn_mode: TurnMode;
  config: SessionConfig;
  version: number;
  created_at: string;
  updated_at?: string;
  personas: SessionPersona[];
}

export interface SessionSummary {
  id: number;
  name: string;
  status: SessionStatus;
  phase: SessionPhase;
  persona_count: number;
  message_count: number;
  created_at: string;
}

// Persona types
export interface PersonaSkill {
  name: string;
  trigger: string;
  use_when: string;
}

export interface PersonaSummary {
  name: string;
  display_name: string;
  description?: string;  // Brief description for tooltip
  domain?: string;
  era?: string;
  voice_preview?: string;
}

export interface PersonaDetail extends PersonaSummary {
  voice_profile?: string;
  core_philosophy?: string;
  methodology?: string;
  skills: PersonaSkill[];
  signature_quotes: string[];
  expertise_summary?: string;
  prompt_preview?: string;
}

export interface SessionPersona {
  id: number;
  persona_name: string;
  display_name?: string;
  provider: string;
  model: string;
  role: string;
  color?: string;
  is_active: boolean;
}

export interface PersonaConfig {
  persona_name: string;
  provider: string;
  model: string;
  role: string;
  color?: string;
}

// Message types
export interface Message {
  id: number;
  persona_name?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  turn_number: number;
  round_number?: number;  // Discussion round within a turn (1=initial, 2+=replies)
  phase?: SessionPhase;
  metadata: Record<string, unknown>;
  created_at: string;
}

// WebSocket event types
export type WSEventType =
  | 'connected'
  | 'disconnected'
  | 'error'
  | 'user_message'
  | 'start_discussion'
  | 'pause_discussion'
  | 'resume_discussion'
  | 'stop_discussion'
  | 'change_phase'
  | 'vote_request'
  | 'persona_thinking'
  | 'persona_chunk'
  | 'persona_done'
  | 'persona_error'
  | 'persona_awaiting_mcp'
  | 'turn_start'
  | 'turn_end'
  | 'speaker_queue'
  | 'consensus_update'
  | 'vote_received'
  | 'vote_complete'
  | 'token_update'
  | 'budget_warning'
  | 'phase_change'
  | 'session_update'
  | 'set_mcp_mode'
  | 'mcp_status'
  | 'orchestrator_status'
  | 'system_message';

export interface WSEvent {
  type: WSEventType;
  data: Record<string, unknown>;
  timestamp: string;
}

// Analytics types
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface TokenUsageSummary {
  session_id: number;
  total: TokenUsage;
  by_persona: Record<string, Omit<TokenUsage, 'total_tokens'>>;
  by_provider: Record<string, Omit<TokenUsage, 'total_tokens'>>;
}

export interface ConsensusMetrics {
  total_proposals: number;
  proposals_with_consensus: number;
  average_agreement: number;
  most_contested?: string;
  votes_by_type: {
    agree: number;
    disagree: number;
    abstain: number;
  };
}

export interface ConversationMetrics {
  total_messages: number;
  messages_by_persona: Record<string, number>;
  messages_by_phase: Record<string, number>;
  average_message_length: number;
  turn_count: number;
}

// Domain types
export interface DomainInfo {
  name: string;
  display_name: string;
  persona_count: number;
}

// Provider types
export interface ProviderInfo {
  available_providers: string[];
  models: Record<string, string[]>;
}
