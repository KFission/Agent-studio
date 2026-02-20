"use client";
import { cn } from "../../lib/cn";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary:
    "bg-jai-primary text-white hover:bg-jai-primary-hover shadow-sm shadow-jai-primary/20 focus-visible:ring-jai-primary/40",
  secondary:
    "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 focus-visible:ring-slate-300",
  ghost:
    "bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-slate-300",
  danger:
    "bg-red-600 text-white hover:bg-red-700 shadow-sm shadow-red-600/20 focus-visible:ring-red-400",
  "danger-outline":
    "bg-white text-red-600 border border-red-200 hover:bg-red-50 hover:border-red-300 focus-visible:ring-red-300",
  brand:
    "bg-jai-navy text-white hover:bg-jai-navy-light shadow-sm focus-visible:ring-jai-navy/40",
};

const SIZES = {
  xs: "text-xs px-2 py-1 gap-1 rounded-md",
  sm: "text-xs px-3 py-1.5 gap-1.5 rounded-lg",
  md: "text-sm px-4 py-2 gap-2 rounded-lg",
  lg: "text-sm px-5 py-2.5 gap-2 rounded-xl",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  icon: Icon,
  iconRight: IconRight,
  loading = false,
  disabled = false,
  className,
  ...props
}) {
  const isDisabled = disabled || loading;
  return (
    <button
      disabled={isDisabled}
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all duration-150 cursor-pointer select-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
        "active:scale-[0.98]",
        VARIANTS[variant] || VARIANTS.primary,
        SIZES[size] || SIZES.md,
        isDisabled && "opacity-50 cursor-not-allowed pointer-events-none",
        className,
      )}
      {...props}
    >
      {loading ? (
        <Loader2 size={size === "xs" ? 12 : 14} className="animate-spin shrink-0" />
      ) : Icon ? (
        <Icon size={size === "xs" ? 12 : 14} className="shrink-0" />
      ) : null}
      {children}
      {IconRight && !loading && <IconRight size={size === "xs" ? 12 : 14} className="shrink-0" />}
    </button>
  );
}

export { VARIANTS as BUTTON_VARIANTS, SIZES as BUTTON_SIZES };
