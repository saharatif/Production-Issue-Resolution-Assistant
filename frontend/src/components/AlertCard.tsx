interface AlertCardProps {
  scanner?: Record<string, unknown> | null;
}

export function AlertCard({ scanner }: AlertCardProps) {
  if (!scanner) {
    return null;
  }
  const details = Array.isArray(scanner.details) ? scanner.details : [];
  return (
    <section className="rounded-md border border-amber-300 bg-amber-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Scanner Alert</h2>
        <span className="rounded-md bg-white px-2 py-1 text-xs font-semibold text-amber-800">
          {String(scanner.severity ?? "UNKNOWN")}
        </span>
      </div>
      <p className="mt-2 text-sm font-medium">{String(scanner.anomaly_type ?? "Anomaly detected")}</p>
      <ul className="mt-3 grid gap-1 text-sm text-slate-700">
        {details.map((detail, index) => (
          <li key={`${detail}-${index}`}>{String(detail)}</li>
        ))}
      </ul>
    </section>
  );
}
