"use client";

import { useWatchlist } from "@/lib/hooks/useWatchlist";
import { useChannels } from "@/lib/hooks/useChannels";
import { useLogs } from "@/lib/hooks/useLogs";

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number | string;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-sm border border-border bg-card p-4">
      <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
        {label}
      </span>
      {loading ? (
        <div className="h-7 w-12 bg-muted animate-pulse rounded-sm" aria-busy="true" />
      ) : (
        <span className="font-mono text-2xl font-bold text-foreground">{value}</span>
      )}
    </div>
  );
}

export function StatsBar() {
  const { data: watchlist, isLoading: wLoading } = useWatchlist();
  const { data: channels, isLoading: cLoading } = useChannels();
  const { data: logs, isLoading: lLoading } = useLogs();

  const activeWatches = watchlist?.filter((w) => w.is_active).length ?? 0;
  const activeChannels = channels?.filter((c) => c.is_active).length ?? 0;
  const now = Date.now();
  const sentLast7d =
    logs?.filter(
      (l) =>
        l.delivery_status === "sent" &&
        now - new Date(l.created_at).getTime() < 7 * 24 * 60 * 60 * 1000
    ).length ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard label="Active Watches" value={activeWatches} loading={wLoading} />
      <StatCard label="Channels" value={activeChannels} loading={cLoading} />
      <StatCard label="Sent (7 days)" value={sentLast7d} loading={lLoading} />
    </div>
  );
}
