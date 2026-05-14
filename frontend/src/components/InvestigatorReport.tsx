import { ConfidenceBar } from "@/components/ConfidenceBar";

interface InvestigatorReportProps {
  report?: Record<string, unknown> | null;
}

export function InvestigatorReport({ report }: InvestigatorReportProps) {
  if (!report) return null;
  const hypotheses = Array.isArray(report.root_cause_hypotheses)
    ? (report.root_cause_hypotheses as Array<Record<string, unknown>>)
    : [];
  const first = hypotheses[0];

  return (
    <section className="rounded-md border border-border bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Investigator Verdict</h2>
        <span className="rounded-md bg-sky-100 px-2 py-1 text-xs font-semibold text-sky-800">
          {String(report.verdict)}
        </span>
      </div>
      {first ? (
        <div className="mt-3 grid gap-3">
          <p className="text-sm">{String(first.hypothesis)}</p>
          <ConfidenceBar
            breakdown={
              first.confidence_breakdown as {
                historical_similarity: number;
                threshold_violation_strength: number;
                maintenance_history_match: number;
                data_completeness: number;
              }
            }
          />
        </div>
      ) : null}
    </section>
  );
}
