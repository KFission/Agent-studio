"use client";
import { useState, useRef, useEffect } from "react";
import { cn } from "../../lib/cn";
import { ChevronDown, Check } from "lucide-react";

export default function Select({
  label,
  hint,
  error,
  value,
  onChange,
  options = [],
  placeholder = "Select...",
  className,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const selected = options.find((o) => (typeof o === "object" ? o.value : o) === value);
  const displayLabel = selected ? (typeof selected === "object" ? selected.label : selected) : null;

  return (
    <div className="w-full" ref={ref}>
      {label && (
        <label className="block text-xs font-medium text-slate-600 mb-1.5">{label}</label>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center justify-between bg-white border rounded-xl px-4 py-2.5 text-sm text-left outline-none transition-all duration-150 cursor-pointer",
          "focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10",
          "disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed",
          error
            ? "border-red-300"
            : open
              ? "border-jai-primary ring-2 ring-jai-primary/10"
              : "border-slate-200 hover:border-slate-300",
          className,
        )}
      >
        <span className={displayLabel ? "text-slate-900" : "text-slate-400"}>
          {displayLabel || placeholder}
        </span>
        <ChevronDown
          size={14}
          className={cn("text-slate-400 transition-transform duration-150 shrink-0", open && "rotate-180")}
        />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-60 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg py-1 animate-in fade-in slide-in-from-top-1 duration-150">
          {options.map((opt) => {
            const optValue = typeof opt === "object" ? opt.value : opt;
            const optLabel = typeof opt === "object" ? opt.label : opt;
            const isActive = optValue === value;
            return (
              <button
                key={optValue}
                type="button"
                onClick={() => {
                  onChange(optValue);
                  setOpen(false);
                }}
                className={cn(
                  "w-full flex items-center gap-2.5 px-4 py-2 text-sm text-left cursor-pointer transition-colors",
                  isActive
                    ? "bg-jai-primary/5 text-jai-primary font-medium"
                    : "text-slate-700 hover:bg-slate-50",
                )}
              >
                <span className="flex-1 truncate">{optLabel}</span>
                {isActive && <Check size={14} className="text-jai-primary shrink-0" />}
              </button>
            );
          })}
          {options.length === 0 && (
            <div className="px-4 py-3 text-sm text-slate-400 text-center">No options</div>
          )}
        </div>
      )}
      {(error || hint) && (
        <p className={cn("text-xs mt-1.5", error ? "text-red-500" : "text-slate-400")}>
          {error || hint}
        </p>
      )}
    </div>
  );
}
