import type { ChangeEvent, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: ReactNode;
}

interface SelectItemProps {
  value: string;
  children: ReactNode;
}

export function Select({ value, onValueChange, children }: SelectProps) {
  return (
    <select
      className="h-11 w-full min-w-0 rounded-md border border-border bg-white px-3 text-sm text-foreground outline-none transition-colors focus:border-primary"
      value={value}
      onChange={(event: ChangeEvent<HTMLSelectElement>) => onValueChange(event.target.value)}
    >
      {children}
    </select>
  );
}

export function SelectItem({ value, children }: SelectItemProps) {
  return <option value={value}>{children}</option>;
}

export function SelectTrigger({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("w-full", className)}>{children}</div>;
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  return placeholder ? <span>{placeholder}</span> : null;
}

export function SelectContent({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
