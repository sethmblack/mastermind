import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useStore } from '@/store';
import { sessionsApi, personasApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { turnModeLabels, turnModeDescriptions, getPersonaColor } from '@/lib/utils';
import type { TurnMode, PersonaConfig, PersonaSummary } from '@/types';
import { Loader2, X, User, ChevronLeft, ChevronRight, Search, ArrowUpDown } from 'lucide-react';

interface EpistemicOptions {
  requireCitations: boolean;
  factChecking: boolean;
  assumptionSurfacing: boolean;
  blindSpotDetection: boolean;
  steelmanMode: boolean;
  devilsAdvocate: boolean;
  webSearchEnabled: boolean;
  codeExecutionEnabled: boolean;
}

type Provider = 'claude-code' | 'ollama' | 'anthropic' | 'openai';

interface ModelInfo {
  id: string;
  label: string;
}

const providerModels: Record<Provider, { label: string; models: ModelInfo[]; defaultModel: string }> = {
  'claude-code': {
    label: 'MCP (Claude Code)',
    defaultModel: 'claude-sonnet-4-20250514',
    models: [
      { id: 'claude-opus-4-5-20251101', label: 'Claude Opus 4.5' },
      { id: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
      { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { id: 'claude-haiku-3-5-20241022', label: 'Claude Haiku 3.5' },
    ],
  },
  ollama: {
    label: 'Ollama (Local)',
    defaultModel: 'llama3.2:3b',
    models: [
      { id: 'llama3.2:3b', label: 'Llama 3.2 3B (Default)' },
      { id: 'llama3.2:1b', label: 'Llama 3.2 1B (Fastest)' },
      { id: 'mistral:7b', label: 'Mistral 7B' },
      { id: 'gemma2:9b', label: 'Gemma2 9B' },
    ],
  },
  anthropic: {
    label: 'Anthropic API',
    defaultModel: 'claude-sonnet-4-20250514',
    models: [
      { id: 'claude-opus-4-5-20251101', label: 'Claude Opus 4.5' },
      { id: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
      { id: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { id: 'claude-haiku-3-5-20241022', label: 'Claude Haiku 3.5' },
    ],
  },
  openai: {
    label: 'OpenAI API',
    defaultModel: 'gpt-4o',
    models: [
      { id: 'gpt-4o', label: 'GPT-4o' },
      { id: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { id: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { id: 'o1', label: 'o1' },
      { id: 'o1-mini', label: 'o1 Mini' },
    ],
  },
};

type Step = 'personas' | 'settings';

type SortMode = 'alphabetical' | 'domain';

export function NewSessionModal() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>('personas');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>('alphabetical');

  // Session settings
  const [name, setName] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [turnMode, setTurnMode] = useState<TurnMode>('round_robin');
  const [defaultProvider, setDefaultProvider] = useState<Provider>('claude-code');
  const [defaultModel, setDefaultModel] = useState(providerModels['claude-code'].defaultModel);
  const [personaProviders, setPersonaProviders] = useState<Record<string, Provider>>({});
  const [personaModels, setPersonaModels] = useState<Record<string, string>>({});
  const [maxRounds, setMaxRounds] = useState(3);
  const [pollMode, setPollMode] = useState(false);
  const [epistemicOptions, setEpistemicOptions] = useState<EpistemicOptions>({
    requireCitations: false,
    factChecking: false,
    assumptionSurfacing: false,
    blindSpotDetection: false,
    steelmanMode: false,
    devilsAdvocate: false,
    webSearchEnabled: false,
    codeExecutionEnabled: false,
  });
  const [isCreating, setIsCreating] = useState(false);

  // Max personas depends on poll mode
  const maxPersonas = pollMode ? 21 : 5;

  // Selected personas for this modal (separate from global store)
  const [selectedPersonas, setSelectedPersonas] = useState<PersonaSummary[]>([]);

  const {
    setCurrentSession,
    setMessages,
    clearSelectedPersonas,
  } = useStore();

  // Fetch personas
  const { data: rawPersonas = [], isLoading: loadingPersonas } = useQuery({
    queryKey: ['personas', { search: searchQuery, domain: selectedDomain }],
    queryFn: () => personasApi.list({
      search: searchQuery || undefined,
      domain: selectedDomain || undefined,
      limit: 300
    }),
    staleTime: 1000 * 60 * 5,
  });

  // Fetch domains for filter
  const { data: domains = [] } = useQuery({
    queryKey: ['domains'],
    queryFn: personasApi.getDomains,
    staleTime: 1000 * 60 * 10,
  });

  // Sort personas based on selected sort mode
  const personas = [...rawPersonas].sort((a, b) => {
    if (sortMode === 'domain') {
      const domainA = a.domain || 'zzz';
      const domainB = b.domain || 'zzz';
      if (domainA !== domainB) return domainA.localeCompare(domainB);
    }
    return a.display_name.localeCompare(b.display_name);
  });

  // Listen for open event
  useEffect(() => {
    const handleOpen = () => {
      setOpen(true);
      setStep('personas');
      setSelectedPersonas([]);
      setSearchQuery('');
    };
    window.addEventListener('open-new-session-modal', handleOpen);
    return () => window.removeEventListener('open-new-session-modal', handleOpen);
  }, []);

  // Initialize persona providers and models when selection changes
  useEffect(() => {
    const newProviders: Record<string, Provider> = {};
    const newModels: Record<string, string> = {};
    selectedPersonas.forEach((p) => {
      const provider = personaProviders[p.name] || defaultProvider;
      newProviders[p.name] = provider;
      newModels[p.name] = personaModels[p.name] || providerModels[provider].defaultModel;
    });
    setPersonaProviders(newProviders);
    setPersonaModels(newModels);
  }, [selectedPersonas, defaultProvider]);

  // Update default model when default provider changes
  useEffect(() => {
    setDefaultModel(providerModels[defaultProvider].defaultModel);
  }, [defaultProvider]);

  const togglePersona = (persona: PersonaSummary) => {
    const isSelected = selectedPersonas.some((p) => p.name === persona.name);
    if (isSelected) {
      setSelectedPersonas(selectedPersonas.filter((p) => p.name !== persona.name));
    } else if (selectedPersonas.length < maxPersonas) {
      setSelectedPersonas([...selectedPersonas, persona]);
    }
  };

  const getProviderForPersona = (personaName: string): Provider => {
    return personaProviders[personaName] || defaultProvider;
  };

  const getModelForPersona = (personaName: string): string => {
    const provider = getProviderForPersona(personaName);
    return personaModels[personaName] || providerModels[provider].defaultModel;
  };

  const setProviderForPersona = (personaName: string, provider: Provider) => {
    setPersonaProviders((prev) => ({ ...prev, [personaName]: provider }));
    // Reset model to default for the new provider
    setPersonaModels((prev) => ({ ...prev, [personaName]: providerModels[provider].defaultModel }));
  };

  const setModelForPersona = (personaName: string, model: string) => {
    setPersonaModels((prev) => ({ ...prev, [personaName]: model }));
  };

  const handleCreate = async () => {
    if (!name.trim() || selectedPersonas.length === 0) return;

    setIsCreating(true);
    try {
      const hasMcpPersona = selectedPersonas.some(
        (p) => getProviderForPersona(p.name) === 'claude-code'
      );

      const personas: PersonaConfig[] = selectedPersonas.map((p, i) => {
        const provider = getProviderForPersona(p.name);
        const actualProvider = provider === 'claude-code' ? 'anthropic' : provider;
        const model = getModelForPersona(p.name);

        return {
          persona_name: p.name,
          provider: actualProvider,
          model: model,
          role: 'participant',
          color: getPersonaColor(i),
        };
      });

      const session = await sessionsApi.create({
        name: name.trim(),
        problem_statement: problemStatement.trim() || undefined,
        personas,
        turn_mode: turnMode,
        config: {
          mcp_mode: hasMcpPersona,
          max_rounds: pollMode ? 1 : maxRounds,  // Poll mode only needs 1 round
          min_rounds: pollMode ? 1 : maxRounds,
          poll_mode: pollMode,
          require_citations: epistemicOptions.requireCitations,
          fact_check: epistemicOptions.factChecking,
          assumption_surfacing: epistemicOptions.assumptionSurfacing,
          blind_spot_detection: epistemicOptions.blindSpotDetection,
          steelman_mode: epistemicOptions.steelmanMode,
          devil_advocate: epistemicOptions.devilsAdvocate,
          web_search_enabled: epistemicOptions.webSearchEnabled,
          code_execution_enabled: epistemicOptions.codeExecutionEnabled,
        },
      });

      setCurrentSession(session);
      setMessages([]);
      clearSelectedPersonas();
      setOpen(false);

      // Reset form
      setName('');
      setProblemStatement('');
      setTurnMode('round_robin');
      setMaxRounds(3);
      setPollMode(false);
      setEpistemicOptions({
        requireCitations: false,
        factChecking: false,
        assumptionSurfacing: false,
        blindSpotDetection: false,
        steelmanMode: false,
        devilsAdvocate: false,
        webSearchEnabled: false,
        codeExecutionEnabled: false,
      });
      setPersonaProviders({});
      setSelectedPersonas([]);
      setStep('personas');
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const applyDefaultToAll = () => {
    const newProviders: Record<string, Provider> = {};
    const newModels: Record<string, string> = {};
    selectedPersonas.forEach((p) => {
      newProviders[p.name] = defaultProvider;
      newModels[p.name] = defaultModel;
    });
    setPersonaProviders(newProviders);
    setPersonaModels(newModels);
  };

  const handleClose = () => {
    setOpen(false);
    setStep('personas');
    setSelectedPersonas([]);
    setSearchQuery('');
    setSelectedDomain(null);
    setSortMode('alphabetical');
    setName('');
    setProblemStatement('');
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {step === 'personas' ? 'Select Personas' : 'Session Settings'}
          </DialogTitle>
          <DialogDescription>
            {step === 'personas'
              ? `Choose up to ${maxPersonas} personas for your ${pollMode ? 'poll' : 'session'} (${selectedPersonas.length}/${maxPersonas} selected)`
              : 'Configure your session settings'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Persona Selection */}
        {step === 'personas' && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Poll Mode Toggle - at the top so it affects persona limit */}
            <div className="p-3 rounded-lg border bg-muted/30 mb-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <Checkbox
                  checked={pollMode}
                  onCheckedChange={(checked) => setPollMode(!!checked)}
                  className="mt-0.5"
                />
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Poll Mode</span>
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">Up to 21 personas</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Questions are treated as polls. Results shown as Simple Majority, Caucus, and Ranked Choice.
                  </p>
                </div>
              </label>
            </div>

            {/* Search and Filters */}
            <div className="space-y-2 mb-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search personas..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Domain filter and Sort */}
              <div className="flex gap-2">
                <Select
                  value={selectedDomain || 'all'}
                  onValueChange={(v) => setSelectedDomain(v === 'all' ? null : v)}
                >
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="All domains" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All domains</SelectItem>
                    {domains.map((domain) => (
                      <SelectItem key={domain.name} value={domain.name}>
                        {domain.display_name} ({domain.persona_count})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={sortMode}
                  onValueChange={(v) => setSortMode(v as SortMode)}
                >
                  <SelectTrigger className="w-40">
                    <ArrowUpDown className="h-4 w-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="alphabetical">A-Z</SelectItem>
                    <SelectItem value="domain">By Domain</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Selected personas chips */}
            {selectedPersonas.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4 pb-4 border-b">
                {selectedPersonas.map((persona, i) => (
                  <div
                    key={persona.name}
                    className="flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: getPersonaColor(i) + '20',
                      color: getPersonaColor(i),
                    }}
                  >
                    {persona.display_name}
                    <button
                      onClick={() => togglePersona(persona)}
                      className="ml-1 hover:bg-black/10 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Persona list - hide already selected personas */}
            <ScrollArea className="h-[400px] -mx-6 px-6">
              {loadingPersonas ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-1">
                  {personas
                    .filter((persona) => !selectedPersonas.some((p) => p.name === persona.name))
                    .map((persona) => {
                    const canSelect = selectedPersonas.length < maxPersonas;

                    return (
                      <button
                        key={persona.name}
                        onClick={() => canSelect && togglePersona(persona)}
                        disabled={!canSelect}
                        className={`
                          text-left px-3 py-2 rounded-lg text-sm transition-colors
                          hover:bg-accent border border-transparent
                          ${!canSelect ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                      >
                        <div className="flex items-center gap-2">
                          <span className="truncate">{persona.display_name}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
          </div>
        )}

        {/* Step 2: Session Settings */}
        {step === 'settings' && (
          <ScrollArea className="h-[450px] -mx-6 px-6">
            <div className="space-y-4 py-2">
              {/* Session Name */}
              <div className="space-y-2">
                <Label htmlFor="name">Session Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Product Strategy Discussion"
                />
              </div>

              {/* Poll Mode indicator (toggle is on step 1) */}
              {pollMode && (
                <div className="p-3 rounded-lg border bg-primary/10 border-primary/30">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-primary">Poll Mode Enabled</span>
                    <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded">{selectedPersonas.length} personas</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Results will show Simple Majority, Caucus, and Ranked Choice voting.
                  </p>
                </div>
              )}

              {/* Problem Statement */}
              <div className="space-y-2">
                <Label htmlFor="problem">{pollMode ? 'Poll Question' : 'Problem Statement'} (optional)</Label>
                <Textarea
                  id="problem"
                  value={problemStatement}
                  onChange={(e) => setProblemStatement(e.target.value)}
                  placeholder={pollMode ? "What question should the personas vote on?" : "What should the personas discuss?"}
                  rows={3}
                />
              </div>

              {/* Turn Mode */}
              <div className="space-y-2">
                <Label>Discussion Mode</Label>
                <Select
                  value={turnMode}
                  onValueChange={(v) => setTurnMode(v as TurnMode)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(turnModeLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value} className="py-2">
                        <div className="flex flex-col items-start">
                          <span className="font-medium">{label}</span>
                          <span className="text-xs text-muted-foreground">
                            {turnModeDescriptions[value]}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Number of Rounds */}
              <div className="space-y-2">
                <Label htmlFor="rounds">Discussion Rounds</Label>
                <div className="flex items-center gap-3">
                  <Input
                    id="rounds"
                    type="number"
                    min={1}
                    value={maxRounds}
                    onChange={(e) => setMaxRounds(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">
                    {maxRounds === 1 ? 'Single response per persona' : `${maxRounds} rounds of discussion`}
                  </span>
                </div>
              </div>

              {/* Epistemic Options */}
              <div className="space-y-3">
                <Label>Epistemic Options</Label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.requireCitations}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, requireCitations: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Require Citations</span>
                      <p className="text-xs text-muted-foreground">Personas must cite sources when making claims</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.factChecking}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, factChecking: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Fact Checking</span>
                      <p className="text-xs text-muted-foreground">Flag claims that need verification</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.assumptionSurfacing}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, assumptionSurfacing: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Assumption Surfacing</span>
                      <p className="text-xs text-muted-foreground">Explicitly identify underlying assumptions</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.blindSpotDetection}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, blindSpotDetection: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Blind Spot Detection</span>
                      <p className="text-xs text-muted-foreground">Point out perspectives being overlooked</p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Debate Modes */}
              <div className="space-y-3">
                <Label>Debate Modes</Label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.steelmanMode}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, steelmanMode: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Steelman Mode</span>
                      <p className="text-xs text-muted-foreground">Present strongest version of opposing arguments</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.devilsAdvocate}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, devilsAdvocate: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Devil's Advocate</span>
                      <p className="text-xs text-muted-foreground">Actively challenge consensus and popular opinions</p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Capabilities */}
              <div className="space-y-3">
                <Label>Capabilities</Label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.webSearchEnabled}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, webSearchEnabled: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Web Search</span>
                      <p className="text-xs text-muted-foreground">Allow personas to search the internet</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <Checkbox
                      checked={epistemicOptions.codeExecutionEnabled}
                      onCheckedChange={(checked) =>
                        setEpistemicOptions((prev) => ({ ...prev, codeExecutionEnabled: !!checked }))
                      }
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <span className="text-sm font-medium">Code Execution</span>
                      <p className="text-xs text-muted-foreground">Allow personas to run code</p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Selected Personas with providers and models */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Personas & AI Models ({selectedPersonas.length}/{maxPersonas})</Label>
                </div>

                {/* Default AI Provider and Model */}
                <div className="flex gap-2 p-2 rounded-lg bg-muted/50">
                  <div className="flex-1 space-y-1">
                    <span className="text-xs text-muted-foreground">Default Provider</span>
                    <Select
                      value={defaultProvider}
                      onValueChange={(v) => setDefaultProvider(v as Provider)}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="claude-code">Claude Code (MCP)</SelectItem>
                        <SelectItem value="ollama">Ollama (Local)</SelectItem>
                        <SelectItem value="anthropic">Anthropic API</SelectItem>
                        <SelectItem value="openai">OpenAI API</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1 space-y-1">
                    <span className="text-xs text-muted-foreground">Default Model</span>
                    <Select
                      value={defaultModel}
                      onValueChange={(v) => setDefaultModel(v)}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {providerModels[defaultProvider].models.map((model) => (
                          <SelectItem key={model.id} value={model.id}>
                            {model.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={applyDefaultToAll}
                      className="text-xs h-8"
                    >
                      Apply to all
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  {selectedPersonas.map((persona, i) => {
                    const provider = getProviderForPersona(persona.name);
                    const availableModels = providerModels[provider].models;
                    return (
                      <div
                        key={persona.name}
                        className="flex items-center gap-2 p-2 rounded-lg border bg-card"
                        style={{ borderColor: getPersonaColor(i) + '50' }}
                      >
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: getPersonaColor(i) + '20' }}
                        >
                          <User className="h-4 w-4" style={{ color: getPersonaColor(i) }} />
                        </div>
                        <span
                          className="flex-1 text-sm font-medium truncate min-w-0"
                          style={{ color: getPersonaColor(i) }}
                        >
                          {persona.display_name}
                        </span>
                        <Select
                          value={getProviderForPersona(persona.name)}
                          onValueChange={(v) => setProviderForPersona(persona.name, v as Provider)}
                        >
                          <SelectTrigger className="w-24 h-8 text-xs flex-shrink-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="claude-code" className="text-xs">MCP</SelectItem>
                            <SelectItem value="ollama" className="text-xs">Ollama</SelectItem>
                            <SelectItem value="anthropic" className="text-xs">Anthropic</SelectItem>
                            <SelectItem value="openai" className="text-xs">OpenAI</SelectItem>
                          </SelectContent>
                        </Select>
                        <Select
                          value={getModelForPersona(persona.name)}
                          onValueChange={(v) => setModelForPersona(persona.name, v)}
                        >
                          <SelectTrigger className="w-36 h-8 text-xs flex-shrink-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {availableModels.map((model) => (
                              <SelectItem key={model.id} value={model.id} className="text-xs">
                                {model.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </ScrollArea>
        )}

        <DialogFooter className="flex-shrink-0 gap-2 sm:gap-2">
          {step === 'personas' ? (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={() => setStep('settings')}
                disabled={selectedPersonas.length === 0}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep('personas')}>
                <ChevronLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || isCreating}
              >
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Start Session'
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
