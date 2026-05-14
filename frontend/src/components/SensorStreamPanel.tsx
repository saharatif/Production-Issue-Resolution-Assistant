import type { SensorReading } from "@/hooks/useSensorStream";
import { cn } from "@/lib/utils";

interface SensorStreamPanelProps {
  readings: SensorReading[];
}

const statusStyles: Record<string, string> = {
  RUNNING: "border-l-emerald-500 bg-emerald-50/70",
  RUNNING_WITH_WARNING: "border-l-amber-500 bg-amber-50/80",
  CRITICAL_TEMPERATURE_SPIKE: "border-l-red-600 bg-red-50/80",
  DATA_GAP: "border-l-red-600 bg-red-50/80",
};

function formatMetric(value: number | null, suffix = "") {
  return value === null ? "No data" : `${value}${suffix}`;
}

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}

export function SensorStreamPanel({ readings }: SensorStreamPanelProps) {
  return (
    <section className="overflow-hidden rounded-md border border-border bg-white">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold">Sensor Stream</h2>
        <span className="text-sm text-muted-foreground">{readings.length} buffered</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] border-collapse text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase tracking-normal text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-semibold">Timestamp</th>
              <th className="px-4 py-3 font-semibold">Line</th>
              <th className="px-4 py-3 font-semibold">Machine</th>
              <th className="px-4 py-3 font-semibold">Temp</th>
              <th className="px-4 py-3 font-semibold">Pressure</th>
              <th className="px-4 py-3 font-semibold">Vibration</th>
              <th className="px-4 py-3 font-semibold">Output</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {readings.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted-foreground" colSpan={8}>
                  Waiting for stream data
                </td>
              </tr>
            ) : (
              readings.map((reading, index) => (
                <tr
                  className={cn(
                    "border-l-4 border-t border-border",
                    statusStyles[reading.machine_status] ?? "border-l-slate-400 bg-white",
                  )}
                  key={`${reading.timestamp}-${reading.line_id}-${index}`}
                >
                  <td className="px-4 py-3 font-mono text-xs">{formatTime(reading.timestamp)}</td>
                  <td className="px-4 py-3 font-semibold">{reading.line_id}</td>
                  <td className="px-4 py-3">{reading.machine_id}</td>
                  <td className="px-4 py-3">{formatMetric(reading.temperature_c, " C")}</td>
                  <td className="px-4 py-3">{formatMetric(reading.pressure_bar, " bar")}</td>
                  <td className="px-4 py-3">{formatMetric(reading.vibration_mm_s, " mm/s")}</td>
                  <td className="px-4 py-3">{formatMetric(reading.output_units_per_hour)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-md border border-border bg-white/80 px-2 py-1 text-xs font-semibold">
                      {reading.machine_status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
