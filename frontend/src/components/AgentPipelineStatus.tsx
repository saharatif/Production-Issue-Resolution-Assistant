import { Check, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface AgentPipelineStatusProps {
  scannerDone: boolean;
  investigatorDone: boolean;
  technicianDone: boolean;
  active: boolean;
}

const steps = [
  ["Scanner", "scannerDone"],
  ["Investigator", "investigatorDone"],
  ["Technician", "technicianDone"],
] as const;

export function AgentPipelineStatus({
  scannerDone,
  investigatorDone,
  technicianDone,
  active,
}: AgentPipelineStatusProps) {
  const values = { scannerDone, investigatorDone, technicianDone };
  return (
    <div className="grid gap-2 rounded-md border border-border bg-white p-4">
      <h2 className="text-base font-semibold">Agent Pipeline</h2>
      <div className="grid gap-2">
        {steps.map(([label, key], index) => {
          const done = values[key];
          const waiting = active && !done && steps.slice(0, index).every(([, prior]) => values[prior]);
          return (
            <div className="flex items-center gap-2 text-sm" key={label}>
              <span
                className={cn(
                  "inline-flex h-7 w-7 items-center justify-center rounded-md border",
                  done ? "border-emerald-600 bg-emerald-50 text-emerald-700" : "border-border bg-slate-50",
                )}
              >
                {done ? (
                  <Check className="h-4 w-4" />
                ) : waiting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Circle className="h-3 w-3" />
                )}
              </span>
              <span className="font-medium">{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
