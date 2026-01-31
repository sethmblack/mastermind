import { useStore } from '@/store';
import { sessionsApi } from '@/lib/api';
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
};

export function SettingsModal() {
  const { settingsOpen, setSettingsOpen, currentSession, setCurrentSession } =
    useStore();

  const config: SessionConfig = currentSession?.config || defaultConfig;

  const handleConfigChange = async (key: string, value: boolean) => {
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
          <DialogTitle>Session Settings</DialogTitle>
          <DialogDescription>
            Configure discussion modes and advanced features
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6">
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
