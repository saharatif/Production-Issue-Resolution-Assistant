interface ConfidenceBreakdown {
  historical_similarity: number;
  threshold_violation_strength: number;
  maintenance_history_match: number;
  data_completeness: number;
}

interface ConfidenceBarProps {
  breakdown: ConfidenceBreakdown;
}

const labels: Record<keyof ConfidenceBreakdown, string> = {
  historical_similarity: "Historical similarity",
  threshold_violation_strength: "Threshold violation",
  maintenance_history_match: "Maintenance match",
  data_completeness: "Data completeness",
};

export function ConfidenceBar({ breakdown }: ConfidenceBarProps) {
  return (
    <div className="grid gap-3">
      {(Object.keys(labels) as Array<keyof ConfidenceBreakdown>).map((key) => {
        const percentage = Math.round(breakdown[key] * 100);

        return (
          <div className="grid gap-1.5" key={key}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium">{labels[key]}</span>
              <span className="font-mono text-xs text-muted-foreground">{percentage}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-sky-600"
                style={{ width: `${Math.min(Math.max(percentage, 0), 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
