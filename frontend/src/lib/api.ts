import type {
  Session,
  SessionSummary,
  SessionConfig,
  PersonaSummary,
  PersonaDetail,
  DomainInfo,
  Message,
  TokenUsageSummary,
  ConsensusMetrics,
  ConversationMetrics,
  ProviderInfo,
  PersonaConfig,
  TurnMode,
} from '@/types';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

// Sessions API
export const sessionsApi = {
  list: (status?: string, limit = 20, offset = 0) =>
    fetchApi<SessionSummary[]>(
      `/sessions/?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ''}`
    ),

  get: (id: number) => fetchApi<Session>(`/sessions/${id}`),

  create: (data: {
    name: string;
    problem_statement?: string;
    personas: PersonaConfig[];
    turn_mode?: TurnMode;
    config?: Partial<SessionConfig>;
  }) =>
    fetchApi<Session>('/sessions/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (
    id: number,
    data: Partial<{
      name: string;
      problem_statement: string;
      phase: string;
      turn_mode: TurnMode;
      status: string;
      config: Partial<SessionConfig>;
    }>
  ) =>
    fetchApi<Session>(`/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    fetchApi<{ status: string; session_id: number }>(`/sessions/${id}`, {
      method: 'DELETE',
    }),

  getMessages: (id: number, limit = 100, offset = 0) =>
    fetchApi<Message[]>(`/sessions/${id}/messages?limit=${limit}&offset=${offset}`),

  getTokenUsage: (id: number) =>
    fetchApi<TokenUsageSummary>(`/sessions/${id}/token-usage`),
};

// Personas API
export const personasApi = {
  list: (params?: { domain?: string; search?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.domain) searchParams.set('domain', params.domain);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    const query = searchParams.toString();
    return fetchApi<PersonaSummary[]>(`/personas/${query ? `?${query}` : ''}`);
  },

  get: (name: string) => fetchApi<PersonaDetail>(`/personas/${encodeURIComponent(name)}`),

  getCount: () => fetchApi<{ count: number }>('/personas/count'),

  getDomains: () => fetchApi<DomainInfo[]>('/personas/domains'),

  getPrompt: (name: string) =>
    fetchApi<{
      persona_name: string;
      display_name: string;
      full_prompt: string;
      system_prompt: string;
    }>(`/personas/${encodeURIComponent(name)}/prompt`),

  getSkillPrompt: (skillName: string) =>
    fetchApi<{
      skill_name: string;
      display_name: string;
      prompt: string;
    }>(`/personas/skills/${encodeURIComponent(skillName)}/prompt`),
};

// Analytics API
export const analyticsApi = {
  getProviders: () => fetchApi<ProviderInfo>('/analytics/providers'),

  getInsights: (sessionId: number, insightType?: string, minImportance = 0) =>
    fetchApi<Array<{
      id: number;
      insight_type: string;
      content: string;
      personas_involved: string[];
      importance: number;
      phase?: string;
      created_at: string;
    }>>(
      `/analytics/sessions/${sessionId}/insights?min_importance=${minImportance}${
        insightType ? `&insight_type=${insightType}` : ''
      }`
    ),

  getVotes: (sessionId: number, proposalId?: string) =>
    fetchApi<Array<{
      id: number;
      proposal: string;
      proposal_id?: string;
      persona_name: string;
      vote: string;
      rank?: number;
      reasoning?: string;
      confidence: number;
      created_at: string;
    }>>(
      `/analytics/sessions/${sessionId}/votes${proposalId ? `?proposal_id=${proposalId}` : ''}`
    ),

  getConsensus: (sessionId: number) =>
    fetchApi<ConsensusMetrics>(`/analytics/sessions/${sessionId}/consensus`),

  getConversationMetrics: (sessionId: number) =>
    fetchApi<ConversationMetrics>(`/analytics/sessions/${sessionId}/conversation-metrics`),

  checkBias: (sessionId: number) =>
    fetchApi<{
      session_id: number;
      groupthink_risk_score: number;
      risk_level: string;
      indicators: string[];
      recommendations: string[];
    }>(`/analytics/sessions/${sessionId}/bias-check`),

  checkScopeCreep: (sessionId: number) =>
    fetchApi<{
      session_id: number;
      scope_creep_score: number;
      risk_level: string;
      original_problem?: string;
      scope_creep_instances: Array<{ content: string; importance: number }>;
      recommendations: string[];
    }>(`/analytics/sessions/${sessionId}/scope-check`),
};

// Config/MCP API
export const configApi = {
  getProviders: () => fetchApi<{
    available_providers: string[];
    models: Record<string, string[]>;
  }>('/config/providers'),

  setApiKey: (provider: string, apiKey: string) =>
    fetchApi<{ status: string; provider: string; configured: boolean }>('/config/api-key', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey }),
    }),

  getMcpStatus: () => fetchApi<{
    status: string;
    tools_count?: number;
    tools?: string[];
    error?: string;
  }>('/config/mcp/status'),

  testMcp: () => fetchApi<{
    status: string;
    test_result?: { domains: Array<{ name: string; persona_count: number }> };
    error?: string;
  }>('/config/mcp/test', { method: 'GET' }),
};

export { ApiError };
