import { useEffect, useState } from "react";

import type { SensorReading } from "@/hooks/useSensorStream";
import { getJson, postJson } from "@/lib/api";

interface PipelineRun {
  run_id?: string;
  issue_id?: string;
  status?: "RUNNING" | "DONE" | "FAILED";
  has_anomaly?: boolean;
  scanner_result?: Record<string, unknown> | null;
  investigator_result?: Record<string, unknown> | null;
  technician_result?: Record<string, unknown> | null;
  approval_status?: string;
  final_report_path?: string | null;
}

export function useAgentPipeline() {
  const [issueId, setIssueId] = useState<string | null>(null);
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze(readings: SensorReading[], scenario: string) {
    setLoading(true);
    setError(null);
    const response = await postJson<{ issue_id: string; status: string }>("/api/issues/analyze", {
      problem_statement: `Analyze ${scenario} production stream`,
      plant_id: "PLANT-01",
      line_id: readings[0]?.line_id ?? "LINE-B",
      raw_sensor_data: readings.slice(0, 20),
      scenario,
    });
    setIssueId(response.issue_id);
    setRun({ issue_id: response.issue_id, status: "RUNNING" });
    setLoading(false);
  }

  async function approve(decision: "approved" | "rejected", notes = "") {
    if (!issueId) return;
    const response = await postJson<{ approval_status: string }>(`/api/issues/${issueId}/approve`, {
      decision,
      approver: "plant_manager",
      notes,
    });
    setRun((current) => (current ? { ...current, approval_status: response.approval_status } : current));
  }

  useEffect(() => {
    if (!issueId) return undefined;
    const interval = window.setInterval(async () => {
      try {
        const nextRun = await getJson<PipelineRun>(`/api/issues/${issueId}`);
        setRun(nextRun);
        if (nextRun.status === "DONE" || nextRun.status === "FAILED") {
          window.clearInterval(interval);
        }
      } catch (pollError) {
        setError(pollError instanceof Error ? pollError.message : "Polling failed");
      }
    }, 1200);
    return () => window.clearInterval(interval);
  }, [issueId]);

  return { analyze, approve, error, issueId, loading, run };
}
