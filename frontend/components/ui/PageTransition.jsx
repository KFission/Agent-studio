"use client";
import { useEffect, useState } from "react";
import { cn } from "../../lib/cn";

export default function PageTransition({ children, pageKey, className }) {
  const [visible, setVisible] = useState(false);
  const [currentKey, setCurrentKey] = useState(pageKey);

  useEffect(() => {
    if (pageKey !== currentKey) {
      setVisible(false);
      const t = setTimeout(() => {
        setCurrentKey(pageKey);
        setVisible(true);
      }, 120);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => setVisible(true), 30);
      return () => clearTimeout(t);
    }
  }, [pageKey, currentKey]);

  return (
    <div
      className={cn(
        "h-full transition-all duration-200 ease-out",
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1.5",
        className,
      )}
    >
      {children}
    </div>
  );
}
