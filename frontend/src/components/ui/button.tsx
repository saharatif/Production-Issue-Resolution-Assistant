import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "default" | "destructive" | "outline";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "default" | "lg";
}

const variants: Record<ButtonVariant, string> = {
  default: "bg-emerald-600 text-white hover:bg-emerald-700",
  destructive: "bg-destructive text-destructive-foreground hover:bg-red-700",
  outline: "border border-border bg-white text-foreground hover:bg-slate-50",
};

export function Button({ className, variant = "default", size = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50",
        size === "lg" ? "h-11 px-5 text-sm" : "h-9 px-3 text-sm",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
