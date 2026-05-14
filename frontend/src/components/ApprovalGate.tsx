import { Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ApprovalGateProps {
  approvalStatus?: string;
  disabled: boolean;
  onApprove: () => void;
  onReject: () => void;
}

export function ApprovalGate({ approvalStatus, disabled, onApprove, onReject }: ApprovalGateProps) {
  return (
    <section className="rounded-md border border-border bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Approval Gate</h2>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold">
          {approvalStatus ?? "not_ready"}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button className="gap-2" disabled={disabled} onClick={onApprove}>
          <Check className="h-4 w-4" />
          Approve
        </Button>
        <Button className="gap-2" disabled={disabled} onClick={onReject} variant="outline">
          <X className="h-4 w-4" />
          Reject
        </Button>
      </div>
    </section>
  );
}
