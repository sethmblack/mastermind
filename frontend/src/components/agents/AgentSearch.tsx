import { useQuery } from '@tanstack/react-query';
import { personasApi } from '@/lib/api';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, ArrowUpDown } from 'lucide-react';

export type SortMode = 'alphabetical' | 'domain';

interface AgentSearchProps {
  value: string;
  onChange: (value: string) => void;
  selectedDomain: string | null;
  onDomainChange: (domain: string | null) => void;
  sortMode?: SortMode;
  onSortChange?: (sort: SortMode) => void;
}

export function AgentSearch({
  value,
  onChange,
  selectedDomain,
  onDomainChange,
  sortMode = 'alphabetical',
  onSortChange,
}: AgentSearchProps) {
  const { data: domains = [] } = useQuery({
    queryKey: ['domains'],
    queryFn: personasApi.getDomains,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });

  return (
    <div className="space-y-2">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search personas..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Domain Filter and Sort */}
      <div className="flex gap-2">
        <Select
          value={selectedDomain || 'all'}
          onValueChange={(v) => onDomainChange(v === 'all' ? null : v)}
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

        {onSortChange && (
          <Select
            value={sortMode}
            onValueChange={(v) => onSortChange(v as SortMode)}
          >
            <SelectTrigger className="w-24">
              <ArrowUpDown className="h-4 w-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="alphabetical">A-Z</SelectItem>
              <SelectItem value="domain">Domain</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  );
}
