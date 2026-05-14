import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem } from "@/components/ui/select";
import { Wifi, WifiOff, Zap } from "lucide-react";

export type DemoScenario = "live" | "pressure_drop" | "temp_spike" | "data_gap" | "high_vibration";

interface TriggerButtonProps {
  active: boolean;
  connected: boolean;
  scenario: DemoScenario;
  onToggle: () => void;
  onScenario: (scenario: DemoScenario) => void;
}

export function TriggerButton({
  active,
  connected,
  scenario,
  onToggle,
  onScenario,
}: TriggerButtonProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="w-full sm:w-72">
        <Select value={scenario} onValueChange={(value) => onScenario(value as DemoScenario)}>
          <SelectContent>
            <SelectItem value="live">Live Stream</SelectItem>
            <SelectItem value="pressure_drop">Demo: LINE-B Pressure Drop</SelectItem>
            <SelectItem value="temp_spike">Demo: Temperature Spike</SelectItem>
            <SelectItem value="data_gap">Demo: Missing Sensor Data</SelectItem>
            <SelectItem value="high_vibration">Demo: High Vibration</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button
        className="w-full gap-2 sm:w-auto"
        size="lg"
        variant={active ? "destructive" : "default"}
        onClick={onToggle}
      >
        <Zap className="h-4 w-4" />
        {active ? "Stop Stream" : "Start Stream"}
      </Button>

      <Badge className="gap-1.5" variant={connected ? "default" : "secondary"}>
        {connected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
        {connected ? "Live" : "Offline"}
      </Badge>
    </div>
  );
}
