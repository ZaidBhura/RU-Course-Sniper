"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorBannerProps {
  error: Error | null;
  className?: string;
}

export function ErrorBanner({ error, className }: ErrorBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  if (!error || dismissed) return null;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start justify-between gap-3 rounded-sm border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive",
        className
      )}
    >
      <span>{error.message || "An unexpected error occurred."}</span>
      <button
        onClick={() => setDismissed(true)}
        className="shrink-0 hover:opacity-70 transition-opacity"
        aria-label="Dismiss error"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
