import { useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { personasApi } from '@/lib/api';
import { AgentCard } from './AgentCard';
import type { PersonaSummary } from '@/types';
import { Loader2 } from 'lucide-react';

interface AgentListProps {
  searchQuery: string;
  selectedDomain: string | null;
}

export function AgentList({ searchQuery, selectedDomain }: AgentListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const { data: personas = [], isLoading } = useQuery({
    queryKey: ['personas', { search: searchQuery, domain: selectedDomain }],
    queryFn: () =>
      personasApi.list({
        search: searchQuery || undefined,
        domain: selectedDomain || undefined,
        limit: 300,
      }),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const rowVirtualizer = useVirtualizer({
    count: personas.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80, // Estimated row height
    overscan: 5,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (personas.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground text-sm">
        No personas found
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="h-full overflow-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const persona = personas[virtualRow.index];
          return (
            <div
              key={virtualRow.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <AgentCard persona={persona} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
