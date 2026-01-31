import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Lightbulb,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Target,
} from 'lucide-react';

interface SummaryPanelProps {
  sessionId: number;
}

export function SummaryPanel({ sessionId }: SummaryPanelProps) {
  const { data: insights = [] } = useQuery({
    queryKey: ['insights', sessionId],
    queryFn: () => analyticsApi.getInsights(sessionId, undefined, 0.3),
    refetchInterval: 10000,
  });

  const consensusInsights = insights.filter(
    (i) => i.insight_type === 'consensus'
  );
  const keyPoints = insights.filter((i) => i.insight_type === 'key_point');
  const actionItems = insights.filter((i) => i.insight_type === 'action_item');
  const questions = insights.filter((i) => i.insight_type === 'question');
  const disagreements = insights.filter(
    (i) => i.insight_type === 'disagreement'
  );

  const getIcon = (type: string) => {
    switch (type) {
      case 'consensus':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'key_point':
        return <Lightbulb className="h-4 w-4 text-yellow-500" />;
      case 'action_item':
        return <Target className="h-4 w-4 text-blue-500" />;
      case 'question':
        return <HelpCircle className="h-4 w-4 text-purple-500" />;
      case 'disagreement':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  if (insights.length === 0) {
    return (
      <div className="text-center text-muted-foreground text-sm py-8">
        No insights yet. Continue the discussion to generate insights.
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-4">
        {/* Consensus */}
        {consensusInsights.length > 0 && (
          <section>
            <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Consensus Points
            </h4>
            <ul className="space-y-2">
              {consensusInsights.map((insight) => (
                <li
                  key={insight.id}
                  className="text-sm p-2 bg-green-500/10 rounded border border-green-500/20"
                >
                  {insight.content}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Key Points */}
        {keyPoints.length > 0 && (
          <section>
            <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-yellow-500" />
              Key Insights
            </h4>
            <ul className="space-y-2">
              {keyPoints.map((insight) => (
                <li
                  key={insight.id}
                  className="text-sm p-2 bg-yellow-500/10 rounded border border-yellow-500/20"
                >
                  {insight.content}
                  {insight.personas_involved.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {insight.personas_involved.map((p) => (
                        <Badge key={p} variant="outline" className="text-xs">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Action Items */}
        {actionItems.length > 0 && (
          <section>
            <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-blue-500" />
              Action Items
            </h4>
            <ul className="space-y-2">
              {actionItems.map((insight) => (
                <li
                  key={insight.id}
                  className="text-sm p-2 bg-blue-500/10 rounded border border-blue-500/20 flex items-start gap-2"
                >
                  <input type="checkbox" className="mt-1" />
                  <span>{insight.content}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Open Questions */}
        {questions.length > 0 && (
          <section>
            <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
              <HelpCircle className="h-4 w-4 text-purple-500" />
              Open Questions
            </h4>
            <ul className="space-y-2">
              {questions.map((insight) => (
                <li
                  key={insight.id}
                  className="text-sm p-2 bg-purple-500/10 rounded border border-purple-500/20"
                >
                  {insight.content}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Disagreements */}
        {disagreements.length > 0 && (
          <section>
            <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              Disagreements
            </h4>
            <ul className="space-y-2">
              {disagreements.map((insight) => (
                <li
                  key={insight.id}
                  className="text-sm p-2 bg-red-500/10 rounded border border-red-500/20"
                >
                  {insight.content}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </ScrollArea>
  );
}
