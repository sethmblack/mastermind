import { useStore } from '@/store';
import { Button } from '@/components/ui/button';
import { Sparkles, Users, MessageSquare, Zap, Plus } from 'lucide-react';

export function WelcomeScreen() {
  const { selectedPersonas } = useStore();

  const handleCreateSession = () => {
    const event = new CustomEvent('open-new-session-modal');
    window.dispatchEvent(event);
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <div className="max-w-2xl text-center">
        {/* Logo/Title */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <Sparkles className="h-12 w-12 text-primary" />
          <h1 className="text-4xl font-bold gradient-text">
            Mastermind
          </h1>
        </div>

        <p className="text-xl text-muted-foreground mb-8">
          Bring together up to 5 AI personas to discuss, debate, and solve problems collaboratively.
        </p>

        {/* Features */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="p-4 rounded-lg bg-card border border-border">
            <Users className="h-8 w-8 text-primary mx-auto mb-2" />
            <h3 className="font-medium">265 Experts</h3>
            <p className="text-sm text-muted-foreground mt-1">
              From Einstein to Feynman, philosophers to CEOs
            </p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <MessageSquare className="h-8 w-8 text-primary mx-auto mb-2" />
            <h3 className="font-medium">Real-time Chat</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Watch personas think and respond in real-time
            </p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <Zap className="h-8 w-8 text-primary mx-auto mb-2" />
            <h3 className="font-medium">Multiple Modes</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Round-robin, debate, consensus, and more
            </p>
          </div>
        </div>

        {/* CTA */}
        <div className="space-y-4">
          {selectedPersonas.length > 0 ? (
            <>
              <p className="text-muted-foreground">
                {selectedPersonas.length} persona{selectedPersonas.length !== 1 ? 's' : ''} selected
              </p>
              <Button size="lg" onClick={handleCreateSession}>
                <Plus className="h-5 w-5 mr-2" />
                Create Session
              </Button>
            </>
          ) : (
            <p className="text-muted-foreground">
              Select personas from the right sidebar to get started
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
