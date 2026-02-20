"use client";
import { cn } from "../../lib/cn";

export default function Card({ children, className, hover = true, onClick, ...props }) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-white border border-slate-200/80 rounded-xl overflow-hidden transition-all duration-200",
        hover && "hover:shadow-md hover:shadow-slate-200/50 hover:border-slate-300/80 hover:scale-[1.005]",
        onClick && "cursor-pointer",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function CardHeader({ children, className, border = true }) {
  return (
    <div
      className={cn(
        "px-5 py-3 flex items-center justify-between",
        border && "border-b border-slate-100",
        className,
      )}
    >
      {children}
    </div>
  );
}

function CardBody({ children, className }) {
  return <div className={cn("p-5", className)}>{children}</div>;
}

function CardFooter({ children, className }) {
  return (
    <div className={cn("px-5 py-3 border-t border-slate-100 bg-slate-50/50", className)}>
      {children}
    </div>
  );
}

export { CardHeader, CardBody, CardFooter };
