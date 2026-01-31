import { ReactNode } from 'react';
import { useStore } from '@/store';
import { cn } from '@/lib/utils';
import {
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AppLayoutProps {
  leftSidebar: ReactNode;
  rightSidebar: ReactNode;
  main: ReactNode;
}

export function AppLayout({ leftSidebar, rightSidebar, main }: AppLayoutProps) {
  const {
    leftSidebarOpen,
    rightSidebarOpen,
    toggleLeftSidebar,
    toggleRightSidebar,
  } = useStore();

  return (
    <div className="flex h-full">
      {/* Left Sidebar */}
      <aside
        className={cn(
          'h-full border-r border-border bg-card transition-all duration-300 ease-in-out',
          leftSidebarOpen ? 'w-80' : 'w-0'
        )}
      >
        <div
          className={cn(
            'h-full w-80 overflow-hidden transition-opacity duration-300',
            leftSidebarOpen ? 'opacity-100' : 'opacity-0'
          )}
        >
          {leftSidebar}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Toggle buttons */}
        <div className="absolute top-4 left-4 z-10">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleLeftSidebar}
            className="h-8 w-8"
          >
            {leftSidebarOpen ? (
              <PanelLeftClose className="h-4 w-4" />
            ) : (
              <PanelLeftOpen className="h-4 w-4" />
            )}
          </Button>
        </div>
        <div className="absolute top-4 right-4 z-10">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleRightSidebar}
            className="h-8 w-8"
          >
            {rightSidebarOpen ? (
              <PanelRightClose className="h-4 w-4" />
            ) : (
              <PanelRightOpen className="h-4 w-4" />
            )}
          </Button>
        </div>

        {main}
      </main>

      {/* Right Sidebar */}
      <aside
        className={cn(
          'h-full border-l border-border bg-card transition-all duration-300 ease-in-out',
          rightSidebarOpen ? 'w-80' : 'w-0'
        )}
      >
        <div
          className={cn(
            'h-full w-80 overflow-hidden transition-opacity duration-300',
            rightSidebarOpen ? 'opacity-100' : 'opacity-0'
          )}
        >
          {rightSidebar}
        </div>
      </aside>
    </div>
  );
}
