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
import { Search } from 'lucide-react';
import { slugToTitle } from '@/lib/utils';

interface AgentSearchProps {
  value: string;
  onChange: (value: string) => void;
  selectedDomain: string | null;
  onDomainChange: (domain: string | null) => void;
}

export function AgentSearch({
  value,
  onChange,
  selectedDomain,
  onDomainChange,
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

      {/* Domain Filter */}
      <Select
        value={selectedDomain || 'all'}
        onValueChange={(v) => onDomainChange(v === 'all' ? null : v)}
      >
        <SelectTrigger>
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
    </div>
  );
}
