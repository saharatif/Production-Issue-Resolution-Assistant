import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center rounded-md px-2.5 text-xs font-semibold",
        variant === "default"
          ? "bg-primary text-primary-foreground"
          : "border border-border bg-white text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
