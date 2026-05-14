import { ConfidenceBar } from "@/components/ConfidenceBar";

interface InvestigatorReportProps {
  report?: Record<string, unknown> | null;
}

function confidencePercent(value: unknown) {
  const confidence = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(confidence)) return "0%";
  return `${Math.round(confidence * 100)}%`;
}

function sourceLabel(report: Record<string, unknown>) {
  if (report.analysis_source === "openai_llm") {
    return `Calculated by LLM${report.model ? ` (${String(report.model)})` : ""}`;
  }
  return "LLM not configured - fallback result";
}

export function InvestigatorReport({ report }: InvestigatorReportProps) {
  if (!report) return null;
  const hypotheses = Array.isArray(report.root_cause_hypotheses)
    ? (report.root_cause_hypotheses as Array<Record<string, unknown>>)
    : [];

  return (
    <section className="grid gap-4 rounded-md border border-border bg-white p-4 lg:col-span-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Root-Cause Hypotheses</h2>
          <p className="mt-1 text-xs font-semibold text-muted-foreground">{sourceLabel(report)}</p>
        </div>
        <div className="grid justify-items-end gap-1">
          <span className="rounded-md bg-sky-100 px-2 py-1 text-xs font-semibold text-sky-800">
            {String(report.verdict)}
          </span>
          {hypotheses[0] ? (
            <span className="text-xl font-bold text-slate-900">
              {confidencePercent(hypotheses[0].confidence)}
            </span>
          ) : null}
        </div>
      </div>
      <div className="grid gap-3">
        {hypotheses.map((hypothesis, index) => {
          const evidence = Array.isArray(hypothesis.supporting_evidence)
            ? hypothesis.supporting_evidence
            : [];

          return (
            <article className="rounded-md border border-border bg-slate-50 p-3" key={index}>
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-semibold">{String(hypothesis.hypothesis)}</p>
                <span className="rounded-md bg-white px-2 py-1 text-sm font-bold text-primary">
                  {confidencePercent(hypothesis.confidence)}
                </span>
              </div>
              <div className="mt-3">
                <ConfidenceBar
                  breakdown={
                    hypothesis.confidence_breakdown as {
                      historical_similarity: number;
                      threshold_violation_strength: number;
                      maintenance_history_match: number;
                      data_completeness: number;
                    }
                  }
                />
              </div>
              {evidence.length > 0 ? (
                <div className="mt-3">
                  <h3 className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
                    Evidence
                  </h3>
                  <ul className="mt-1 grid gap-1 text-sm text-slate-700">
                    {evidence.map((item, evidenceIndex) => (
                      <li key={`${String(item)}-${evidenceIndex}`}>{String(item)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
