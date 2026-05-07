"use client";

import Link from "next/link";
import { useLogs } from "@/lib/hooks/useLogs";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { IndexNumber } from "@/components/shared/IndexNumber";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatTimestamp } from "@/lib/utils/formatters";
import type { NotificationLogOut } from "@/lib/schemas/logs";

function ActivityRow({ log }: { log: NotificationLogOut }) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-border/50 last:border-0">
      <IndexNumber value={log.index_number} className="text-foreground w-14 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-foreground truncate">
          {log.course_title
            ? `${log.course_subject} ${log.course_number} — ${log.course_title}`
            : `Index ${log.index_number}`}
        </p>
        <p className="text-xs text-muted-foreground font-mono">{formatTimestamp(log.created_at)}</p>
      </div>
      <StatusBadge
        status={log.delivery_status as "sent" | "failed" | "skipped"}
        className="shrink-0"
      />
    </div>
  );
}

export function RecentActivityFeed() {
  const { data: logs, isLoading } = useLogs();
  const recent = logs?.slice(0, 5) ?? [];

  return (
    <div className="rounded-sm border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
          Recent Activity
        </h2>
        <Link
          href="/dashboard/logs"
          className="text-xs text-primary hover:underline font-mono"
        >
          View all →
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded-sm" aria-busy="true" />
          ))}
        </div>
      ) : recent.length === 0 ? (
        <EmptyState
          title="No notifications yet"
          description="When a watched course opens, you'll see it here."
        />
      ) : (
        <div>{recent.map((log) => <ActivityRow key={log.id} log={log} />)}</div>
      )}
    </div>
  );
}
