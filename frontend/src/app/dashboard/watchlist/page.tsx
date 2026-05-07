import { TopBar } from "@/components/layout/TopBar";
import { WatchlistTable } from "@/components/watchlist/WatchlistTable";
import { AddWatchedIndexDialog } from "@/components/watchlist/AddWatchedIndexDialog";

export default function WatchlistPage() {
  return (
    <>
      <TopBar title="Watchlist" />
      <div className="p-6 space-y-4 max-w-4xl">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground font-mono">
            Courses being monitored for open seats
          </p>
          <AddWatchedIndexDialog />
        </div>
        <WatchlistTable />
      </div>
    </>
  );
}
