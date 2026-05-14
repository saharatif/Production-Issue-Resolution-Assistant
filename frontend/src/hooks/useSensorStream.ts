import { useEffect, useRef, useState } from "react";

import { sensorStreamUrl } from "@/lib/api";

export interface SensorReading {
  timestamp: string;
  plant_id: string;
  line_id: string;
  machine_id: string;
  temperature_c: number | null;
  pressure_bar: number | null;
  vibration_mm_s: number | null;
  output_units_per_hour: number | null;
  machine_status: string;
}

const BUFFER_CAP = 200;

export function useSensorStream(active: boolean, scenario: string) {
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    eventSourceRef.current?.close();

    if (!active) {
      setConnected(false);
      return undefined;
    }

    const eventSource = new EventSource(sensorStreamUrl(scenario));
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => setConnected(true);
    eventSource.onerror = () => setConnected(false);
    eventSource.onmessage = (event) => {
      const batch = JSON.parse(event.data) as SensorReading[];
      setReadings((previous) => [...batch, ...previous].slice(0, BUFFER_CAP));
    };

    return () => {
      eventSource.close();
      setConnected(false);
    };
  }, [active, scenario]);

  return { readings, connected };
}
