import { useState } from "react";

import { ActionPlanPanel } from "@/components/ActionPlanPanel";
import { AgentPipelineStatus } from "@/components/AgentPipelineStatus";
import { AlertCard } from "@/components/AlertCard";
import { ApprovalGate } from "@/components/ApprovalGate";
import { InvestigatorReport } from "@/components/InvestigatorReport";
import { SensorStreamPanel } from "@/components/SensorStreamPanel";
import { type DemoScenario, TriggerButton } from "@/components/TriggerButton";
import { Button } from "@/components/ui/button";
import { useAgentPipeline } from "@/hooks/useAgentPipeline";
import { useSensorStream } from "@/hooks/useSensorStream";
import { reportPdfUrl } from "@/lib/api";

export default function App() {
  const [active, setActive] = useState(false);
  const [scenario, setScenario] = useState<DemoScenario>("live");
  const { readings, connected } = useSensorStream(active, scenario);
  const pipeline = useAgentPipeline();
  const run = pipeline.run;
  const scannerDone = Boolean(run?.scanner_result);
  const investigatorDone = Boolean(run?.investigator_result);
  const technicianDone = Boolean(run?.technician_result);
  const issueId = pipeline.issueId ?? run?.run_id ?? run?.issue_id ?? null;

  return (
    <main className="min-h-screen">
      <div className="mx-auto grid w-full max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-normal text-primary">PLANT-01</p>
            <h1 className="mt-1 text-2xl font-bold sm:text-3xl">
              Production Issue Resolution Assistant
            </h1>
          </div>
          <TriggerButton
            active={active}
            connected={connected}
            scenario={scenario}
            onScenario={setScenario}
            onToggle={() => setActive((value) => !value)}
          />
        </header>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <SensorStreamPanel readings={readings} />

          <aside className="grid content-start gap-4">
            <div className="rounded-md border border-border bg-white p-4">
              <div className="mb-4">
                <h2 className="text-base font-semibold">Pipeline Trigger</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Send the current sensor buffer through the three-agent workflow.
                </p>
              </div>
              <Button
                className="w-full"
                disabled={pipeline.loading}
                onClick={() => void pipeline.analyze(readings, scenario)}
              >
                Run Agent Analysis
              </Button>
              {pipeline.error ? <p className="mt-2 text-sm text-red-700">{pipeline.error}</p> : null}
            </div>
            <AgentPipelineStatus
              active={run?.status === "RUNNING"}
              scannerDone={scannerDone}
              investigatorDone={investigatorDone}
              technicianDone={technicianDone}
            />
            <ApprovalGate
              approvalStatus={run?.approval_status}
              disabled={!technicianDone || run?.approval_status !== "pending"}
              onApprove={() => void pipeline.approve("approved")}
              onReject={() => void pipeline.approve("rejected")}
            />
            {issueId && technicianDone ? (
              <a
                className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-white px-3 text-sm font-semibold"
                href={reportPdfUrl(issueId)}
              >
                Download PDF
              </a>
            ) : null}
          </aside>
        </div>
        <div className="grid gap-5 lg:grid-cols-3">
          <AlertCard scanner={run?.scanner_result} />
          <InvestigatorReport report={run?.investigator_result} />
          <ActionPlanPanel technician={run?.technician_result} />
        </div>
      </div>
    </main>
  );
}
