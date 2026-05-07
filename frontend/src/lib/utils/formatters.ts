export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatAbsoluteTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatSemesterCode(code: string): string {
  const seasonMap: Record<string, string> = {
    "0": "Winter",
    "1": "Spring",
    "7": "Summer",
    "9": "Fall",
  };
  if (code.length !== 5) return code;
  const seasonDigit = code[0];
  const year = code.slice(1);
  const season = seasonMap[seasonDigit] ?? "Unknown";
  return `${season} ${year}`;
}

export function formatEventType(eventType: string): string {
  return eventType === "open_notify" ? "Course Opened" : "Course Closed";
}

export function formatDeliveryStatus(status: string): {
  label: string;
  colorClass: string;
} {
  switch (status) {
    case "sent":
      return { label: "Sent", colorClass: "text-[#00c896]" };
    case "failed":
      return { label: "Failed", colorClass: "text-destructive" };
    case "skipped":
      return { label: "Skipped", colorClass: "text-muted-foreground" };
    default:
      return { label: status, colorClass: "text-muted-foreground" };
  }
}

export function formatChannelType(channelType: string): string {
  return channelType === "discord" ? "Discord" : "Pushover";
}

export function padIndex(n: number): string {
  return String(n).padStart(5, "0");
}
