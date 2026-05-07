"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { IndexNumber } from "@/components/shared/IndexNumber";
import { LoadingRow } from "@/components/shared/LoadingRow";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { LogsFilter, type LogFilters } from "./LogsFilter";
import { useLogs } from "@/lib/hooks/useLogs";
import {
  formatAbsoluteTimestamp,
  formatEventType,
  formatChannelType,
} from "@/lib/utils/formatters";
import type { NotificationLogOut } from "@/lib/schemas/logs";
import { ExternalLink } from "lucide-react";

function LogRow({ log }: { log: NotificationLogOut }) {
  const courseLabel =
    log.course_title
      ? `${log.course_subject ?? ""} ${log.course_number ?? ""} — ${log.course_title}`.trim()
      : null;

  return (
    <TableRow className="border-border hover:bg-accent/30 transition-colors">
      <TableCell className="text-xs font-mono text-muted-foreground whitespace-nowrap">
        {formatAbsoluteTimestamp(log.created_at)}
      </TableCell>
      <TableCell className="font-mono">
        <IndexNumber value={log.index_number} />
      </TableCell>
      <TableCell className="text-xs text-muted-foreground max-w-[180px] truncate">
        {courseLabel ?? <span className="italic opacity-50">—</span>}
      </TableCell>
      <TableCell className="text-xs font-mono text-muted-foreground">
        {formatEventType(log.event_type)}
      </TableCell>
      <TableCell className="text-xs font-mono text-muted-foreground">
        {formatChannelType(log.channel_type)}
      </TableCell>
      <TableCell>
        <StatusBadge
          status={log.delivery_status as "sent" | "failed" | "skipped"}
        />
      </TableCell>
      <TableCell>
        {log.webreg_url ? (
          <a
            href={log.webreg_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-mono text-primary hover:underline"
            aria-label={`WebReg link for index ${log.index_number}`}
          >
            WebReg <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
        ) : null}
      </TableCell>
    </TableRow>
  );
}

export function LogsTable() {
  const { data: logs, isLoading, error } = useLogs();
  const [filters, setFilters] = useState<LogFilters>({
    status: "",
    channel: "",
    eventType: "",
  });

  const filtered = logs?.filter((l) => {
    if (filters.status && l.delivery_status !== filters.status) return false;
    if (filters.channel && l.channel_type !== filters.channel) return false;
    if (filters.eventType && l.event_type !== filters.eventType) return false;
    return true;
  }) ?? [];

  return (
    <div className="space-y-4">
      <ErrorBanner error={error as Error | null} />
      <LogsFilter filters={filters} onChange={setFilters} />

      {isLoading ? (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Time", "Index", "Course", "Event", "Channel", "Status", ""].map((h) => (
                <TableHead key={h} className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {[0, 1, 2].map((i) => <LoadingRow key={i} cols={7} />)}
          </TableBody>
        </Table>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={logs?.length === 0 ? "No notifications yet" : "No results match your filters"}
          description={
            logs?.length === 0
              ? "When a watched course opens, you'll see it here."
              : "Try adjusting the filters above."
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Time", "Index", "Course", "Event", "Channel", "Status", ""].map((h) => (
                <TableHead
                  key={h}
                  scope="col"
                  className="text-xs font-mono text-muted-foreground uppercase tracking-widest"
                >
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((log) => <LogRow key={log.id} log={log} />)}
          </TableBody>
        </Table>
      )}

      {!isLoading && logs && logs.length > 0 && (
        <p className="text-xs text-muted-foreground font-mono text-right">
          Showing {filtered.length} of {logs.length} entries
        </p>
      )}
    </div>
  );
}
