"use client";
import { useEffect, useRef } from "react";
import { cn } from "../../lib/cn";
import { X } from "lucide-react";

export default function Dialog({ open, onClose, children, className, size = "md" }) {
  const overlayRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const SIZES = {
    sm: "max-w-sm",
    md: "max-w-lg",
    lg: "max-w-2xl",
    xl: "max-w-4xl",
    full: "max-w-[90vw]",
  };

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={(e) => { if (e.target === overlayRef.current) onClose?.(); }}
    >
      <div
        className={cn(
          "bg-white rounded-2xl shadow-2xl w-full mx-4 overflow-hidden",
          "animate-in zoom-in-95 fade-in slide-in-from-bottom-2 duration-200",
          SIZES[size] || SIZES.md,
          className,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function DialogHeader({ children, title, subtitle, onClose, className }) {
  return (
    <div className={cn("px-6 py-4 border-b border-slate-200 flex items-center justify-between", className)}>
      <div className="flex-1 min-w-0">
        {title && <h3 className="text-base font-semibold text-slate-900">{title}</h3>}
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        {children}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 cursor-pointer transition shrink-0 ml-3"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}

function DialogBody({ children, className }) {
  return <div className={cn("px-6 py-4", className)}>{children}</div>;
}

function DialogFooter({ children, className }) {
  return (
    <div className={cn("px-6 py-3 border-t border-slate-100 flex justify-end gap-2", className)}>
      {children}
    </div>
  );
}

export { DialogHeader, DialogBody, DialogFooter };
