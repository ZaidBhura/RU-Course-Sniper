import { cn } from "@/lib/utils";

type Status =
  | "sent"
  | "failed"
  | "skipped"
  | "open"
  | "closed"
  | "active"
  | "inactive";

const config: Record<Status, { label: string; textColor: string; border: string }> = {
  sent:     { label: "Sent",     textColor: "text-[#00c896]", border: "border-l-[#00c896]" },
  open:     { label: "Open",     textColor: "text-[#00c896]", border: "border-l-[#00c896]" },
  active:   { label: "Active",   textColor: "text-[#00c896]", border: "border-l-[#00c896]" },
  failed:   { label: "Failed",   textColor: "text-destructive", border: "border-l-destructive" },
  closed:   { label: "Closed",   textColor: "text-destructive", border: "border-l-destructive" },
  skipped:  { label: "Skipped",  textColor: "text-muted-foreground", border: "border-l-muted-foreground" },
  inactive: { label: "Inactive", textColor: "text-muted-foreground", border: "border-l-muted-foreground" },
};

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { label, textColor, border } = config[status];
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 border-l-[3px] text-xs font-mono uppercase tracking-widest",
        textColor,
        border,
        className
      )}
    >
      {label}
    </span>
  );
}
