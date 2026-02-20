"use client";
import { forwardRef } from "react";
import { cn } from "../../lib/cn";

const Textarea = forwardRef(function Textarea(
  { label, hint, error, className, id, ...props },
  ref,
) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-slate-600 mb-1.5">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={inputId}
        className={cn(
          "w-full bg-white border rounded-xl px-4 py-2.5 text-sm text-slate-900 outline-none transition-all duration-150 resize-y",
          "placeholder:text-slate-400",
          "focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10",
          "disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed",
          error
            ? "border-red-300 focus:border-red-400 focus:ring-red-100"
            : "border-slate-200 hover:border-slate-300",
          className,
        )}
        {...props}
      />
      {(error || hint) && (
        <p className={cn("text-xs mt-1.5", error ? "text-red-500" : "text-slate-400")}>
          {error || hint}
        </p>
      )}
    </div>
  );
});

export default Textarea;
