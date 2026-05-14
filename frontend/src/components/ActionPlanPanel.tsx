interface ActionPlanPanelProps {
  technician?: Record<string, unknown> | null;
}

function FieldBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border bg-slate-50 p-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-slate-700">
        {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export function ActionPlanPanel({ technician }: ActionPlanPanelProps) {
  if (!technician) return null;
  return (
    <section className="grid gap-3 rounded-md border border-border bg-white p-4">
      <h2 className="text-base font-semibold">Technician Action Package</h2>
      <FieldBlock title="Shift Handoff" value={technician.shift_handoff_note} />
      <FieldBlock title="Maintenance Request" value={technician.maintenance_request} />
      <FieldBlock title="Corrective Action Plan" value={technician.corrective_action_plan} />
    </section>
  );
}
