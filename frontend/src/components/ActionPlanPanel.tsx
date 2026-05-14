interface ActionPlanPanelProps {
  technician?: Record<string, unknown> | null;
}

function Field({ label, value }: { label: string; value?: unknown }) {
  if (!value) return null;
  return (
    <div className="grid grid-cols-[160px_1fr] gap-x-2 text-sm">
      <span className="font-medium text-slate-500">{label}</span>
      <span className="text-slate-800">{String(value)}</span>
    </div>
  );
}

function BulletList({ label, items }: { label: string; items?: unknown }) {
  const list = Array.isArray(items) ? items : [];
  return (
    <div className="text-sm">
      <span className="font-medium text-slate-500">{label}</span>
      {list.length === 0 ? (
        <p className="ml-1 mt-1 text-slate-400 italic">None</p>
      ) : (
        <ul className="ml-4 mt-1 list-disc space-y-0.5 text-slate-800">
          {list.map((item, i) => (
            <li key={i}>{String(item)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-slate-50 p-4 grid gap-2">
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      <div className="grid gap-2">{children}</div>
    </div>
  );
}

function ShiftHandoff({ note }: { note: Record<string, unknown> }) {
  return (
    <SectionCard title="Shift Handoff Note">
      <Field label="Title" value={note.title} />
      <Field label="Summary" value={note.summary} />
      <Field label="Current Status" value={note.current_status} />
      <BulletList label="Actions Completed" items={note.actions_completed} />
      <BulletList label="Open Actions" items={note.open_actions} />
    </SectionCard>
  );
}

function MaintenanceRequest({ req }: { req: Record<string, unknown> }) {
  return (
    <SectionCard title="Maintenance Request">
      <Field label="Priority" value={req.priority} />
      <Field label="Asset" value={req.asset} />
      <Field label="Line" value={req.line_id} />
      <Field label="Request" value={req.request} />
      <Field label="Reason" value={req.reason} />
    </SectionCard>
  );
}

function CorrectiveActionPlan({ cap }: { cap: Record<string, unknown> }) {
  return (
    <SectionCard title="Corrective Action Plan">
      <Field label="Problem" value={cap.problem} />
      <Field label="Containment" value={cap.containment} />
      <Field label="Root Cause Analysis" value={cap.root_cause_analysis} />
      <Field label="Corrective Action" value={cap.corrective_action} />
      <Field label="Preventive Action" value={cap.preventive_action} />
    </SectionCard>
  );
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function ActionPlanPanel({ technician }: ActionPlanPanelProps) {
  if (!technician) return null;
  return (
    <section className="grid gap-3 rounded-md border border-border bg-white p-4">
      <h2 className="text-base font-semibold">Technician Action Package</h2>
      {isRecord(technician.shift_handoff_note) && (
        <ShiftHandoff note={technician.shift_handoff_note} />
      )}
      {isRecord(technician.maintenance_request) && (
        <MaintenanceRequest req={technician.maintenance_request} />
      )}
      {isRecord(technician.corrective_action_plan) && (
        <CorrectiveActionPlan cap={technician.corrective_action_plan} />
      )}
    </section>
  );
}
