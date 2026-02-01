import { useStore } from '@/store';
import { sessionsApi, configApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { useState, useEffect } from 'react';
import { wsClient } from '@/lib/websocket';
import type { SessionConfig } from '@/types';

const defaultConfig: SessionConfig = {
  require_citations: false,
  steelman_mode: false,
  devil_advocate: false,
  fact_check: false,
  assumption_surfacing: false,
  blind_spot_detection: false,
  web_search_enabled: false,
  code_execution_enabled: false,
  mcp_mode: false,
  min_rounds: 3,
  max_rounds: 3,
};

interface ProviderStatus {
  anthropic: boolean;
  openai: boolean;
  ollama: boolean;
  mcp: boolean;
  mcpTools?: string[];
}

export function SettingsModal() {
  const { settingsOpen, setSettingsOpen, currentSession, setCurrentSession } =
    useStore();

  const config: SessionConfig = currentSession?.config || defaultConfig;

  const [apiKey, setApiKey] = useState('');
  const [apiKeySaved, setApiKeySaved] = useState(false);
  const [providers, setProviders] = useState<ProviderStatus | null>(null);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [wsConnected, setWsConnected] = useState(wsClient.isConnected);

  // Check provider status
  const checkProviders = async () => {
    setLoadingProviders(true);
    try {
      const [providerData, mcpData] = await Promise.all([
        configApi.getProviders(),
        configApi.getMcpStatus(),
      ]);
      setProviders({
        anthropic: providerData.available_providers?.includes('anthropic') ?? false,
        openai: providerData.available_providers?.includes('openai') ?? false,
        ollama: providerData.available_providers?.includes('ollama') ?? false,
        mcp: mcpData.status === 'available',
        mcpTools: mcpData.tools,
      });
    } catch (e) {
      console.error('Failed to check providers:', e);
      setProviders({ anthropic: false, openai: false, ollama: false, mcp: false });
    }
    setLoadingProviders(false);
  };

  // Test MCP connection by executing a tool
  const [mcpTesting, setMcpTesting] = useState(false);
  const [mcpTestResult, setMcpTestResult] = useState<string | null>(null);

  const testMcpConnection = async () => {
    setMcpTesting(true);
    setMcpTestResult(null);
    try {
      const result = await configApi.testMcp();
      if (result.status === 'success' && result.test_result?.domains) {
        setMcpTestResult(`Success! Found ${result.test_result.domains.length} domains`);
      } else {
        setMcpTestResult(`Error: ${result.error || 'Unknown error'}`);
      }
    } catch (e) {
      setMcpTestResult(`Failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
    setMcpTesting(false);
  };

  // Check WebSocket connection
  useEffect(() => {
    const interval = setInterval(() => {
      setWsConnected(wsClient.isConnected);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Load provider status when modal opens
  useEffect(() => {
    if (settingsOpen) {
      checkProviders();
    }
  }, [settingsOpen]);

  const handleSaveApiKey = async () => {
    try {
      const response = await fetch('/api/config/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'anthropic', api_key: apiKey }),
      });
      if (response.ok) {
        setApiKeySaved(true);
        setApiKey('');
        setTimeout(() => setApiKeySaved(false), 3000);
        checkProviders();
      }
    } catch (e) {
      console.error('Failed to save API key:', e);
    }
  };

  const handleConfigChange = async (key: string, value: boolean | number) => {
    if (!currentSession) return;

    const updated = await sessionsApi.update(currentSession.id, {
      config: {
        ...config,
        [key]: value,
      },
    });
    setCurrentSession(updated);
  };

  return (
    <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Configure AI providers and session settings
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6">
            {/* Connection Status */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Connection Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">WebSocket</span>
                  </div>
                  {wsConnected ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Connected
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <XCircle className="h-3 w-3 mr-1" />
                      Disconnected
                    </Badge>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">Anthropic API</span>
                  </div>
                  {loadingProviders ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : providers?.anthropic ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Connected
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <XCircle className="h-3 w-3 mr-1" />
                      Not configured
                    </Badge>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">OpenAI API</span>
                  </div>
                  {loadingProviders ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : providers?.openai ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Connected
                    </Badge>
                  ) : (
                    <Badge variant="secondary">
                      <XCircle className="h-3 w-3 mr-1" />
                      Not configured
                    </Badge>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">Ollama (Local)</span>
                  </div>
                  {loadingProviders ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : providers?.ollama ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Running
                    </Badge>
                  ) : (
                    <Badge variant="secondary">
                      <XCircle className="h-3 w-3 mr-1" />
                      Not running
                    </Badge>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">MCP Server</span>
                    {providers?.mcpTools && (
                      <span className="text-xs text-muted-foreground">
                        ({providers.mcpTools.length} tools)
                      </span>
                    )}
                  </div>
                  {loadingProviders ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : providers?.mcp ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Available
                    </Badge>
                  ) : (
                    <Badge variant="secondary">
                      <XCircle className="h-3 w-3 mr-1" />
                      Not available
                    </Badge>
                  )}
                </div>

                {providers?.mcp && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={testMcpConnection}
                      disabled={mcpTesting}
                    >
                      {mcpTesting ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : null}
                      Test MCP Connection
                    </Button>
                    {mcpTestResult && (
                      <span className={`text-xs ${mcpTestResult.startsWith('Success') ? 'text-green-600' : 'text-red-500'}`}>
                        {mcpTestResult}
                      </span>
                    )}
                  </div>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={checkProviders}
                  disabled={loadingProviders}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${loadingProviders ? 'animate-spin' : ''}`} />
                  Refresh Status
                </Button>
              </div>
            </section>

            <Separator />

            {/* Claude Code Mode */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Claude Code Mode</h3>
              <div className="space-y-4">
                <SettingSwitch
                  label="Use Claude Code as AI Provider"
                  description="When enabled, Claude Code generates persona responses via MCP instead of calling the API directly. No API key required."
                  checked={config.mcp_mode}
                  onCheckedChange={(v) => {
                    handleConfigChange('mcp_mode', v);
                    // Also send WebSocket event to enable MCP mode on the orchestrator
                    wsClient.send({ type: 'set_mcp_mode', data: { enabled: v } });
                  }}
                />
                {config.mcp_mode && (
                  <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                    <p className="text-xs text-blue-400">
                      <strong>Claude Code Mode Active:</strong> When you send a message, the app will wait for Claude Code to generate responses for each persona. Use the MCP tools to provide responses.
                    </p>
                  </div>
                )}
              </div>
            </section>

            <Separator />

            {/* Discussion Rounds */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Discussion Rounds</h3>
              <p className="text-xs text-muted-foreground mb-3">
                Configure how many rounds of discussion personas engage in. Each round, personas respond to what others have said.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="min-rounds" className="text-sm">Minimum Rounds</Label>
                  <Input
                    id="min-rounds"
                    type="number"
                    min={1}
                    max={10}
                    value={config.min_rounds || 3}
                    onChange={(e) => {
                      const value = parseInt(e.target.value) || 3;
                      handleConfigChange('min_rounds', value);
                    }}
                    className="w-full"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max-rounds" className="text-sm">Maximum Rounds</Label>
                  <Input
                    id="max-rounds"
                    type="number"
                    min={1}
                    max={10}
                    value={config.max_rounds || 3}
                    onChange={(e) => {
                      const value = parseInt(e.target.value) || 3;
                      handleConfigChange('max_rounds', value);
                    }}
                    className="w-full"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Round 1 = Initial responses, Round 2+ = Discussion/debate, Final round = Synthesis
              </p>
            </section>

            <Separator />

            {/* API Key Input */}
            <section>
              <h3 className="text-sm font-semibold mb-4">API Key (Standalone Mode)</h3>
              <p className="text-xs text-muted-foreground mb-3">
                {config.mcp_mode
                  ? "API key not needed when Claude Code mode is enabled."
                  : "Enter your Anthropic API key to enable AI responses. The key is stored in the backend .env file."
                }
              </p>
              <div className="flex gap-2">
                <Input
                  type="password"
                  placeholder="sk-ant-api03-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="flex-1"
                />
                <Button onClick={handleSaveApiKey} disabled={!apiKey}>
                  {apiKeySaved ? (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Saved
                    </>
                  ) : (
                    'Save'
                  )}
                </Button>
              </div>
            </section>

            <Separator />

            {/* Discussion Quality */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Discussion Quality</h3>
              <div className="space-y-4">
                <SettingSwitch
                  label="Require Citations"
                  description="Personas must cite sources when making claims"
                  checked={config.require_citations}
                  onCheckedChange={(v) => handleConfigChange('require_citations', v)}
                />
                <SettingSwitch
                  label="Fact Checking"
                  description="Flag claims that need verification"
                  checked={config.fact_check}
                  onCheckedChange={(v) => handleConfigChange('fact_check', v)}
                />
                <SettingSwitch
                  label="Assumption Surfacing"
                  description="Explicitly identify underlying assumptions"
                  checked={config.assumption_surfacing}
                  onCheckedChange={(v) => handleConfigChange('assumption_surfacing', v)}
                />
                <SettingSwitch
                  label="Blind Spot Detection"
                  description="Point out perspectives being overlooked"
                  checked={config.blind_spot_detection}
                  onCheckedChange={(v) => handleConfigChange('blind_spot_detection', v)}
                />
              </div>
            </section>

            <Separator />

            {/* Debate Modes */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Debate Modes</h3>
              <div className="space-y-4">
                <SettingSwitch
                  label="Steelman Mode"
                  description="Present strongest version of opposing arguments"
                  checked={config.steelman_mode}
                  onCheckedChange={(v) => handleConfigChange('steelman_mode', v)}
                />
                <SettingSwitch
                  label="Devil's Advocate"
                  description="Actively challenge consensus and popular opinions"
                  checked={config.devil_advocate}
                  onCheckedChange={(v) => handleConfigChange('devil_advocate', v)}
                />
              </div>
            </section>

            <Separator />

            {/* Tools */}
            <section>
              <h3 className="text-sm font-semibold mb-4">Tools & Capabilities</h3>
              <div className="space-y-4">
                <SettingSwitch
                  label="Web Search"
                  description="Allow personas to search the web for information"
                  checked={config.web_search_enabled}
                  onCheckedChange={(v) => handleConfigChange('web_search_enabled', v)}
                />
                <SettingSwitch
                  label="Code Execution"
                  description="Allow personas to run code in a sandbox"
                  checked={config.code_execution_enabled}
                  onCheckedChange={(v) => handleConfigChange('code_execution_enabled', v)}
                />
              </div>
            </section>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

interface SettingSwitchProps {
  label: string;
  description: string;
  checked?: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function SettingSwitch({
  label,
  description,
  checked,
  onCheckedChange,
}: SettingSwitchProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="space-y-0.5">
        <Label className="text-sm font-medium">{label}</Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}
