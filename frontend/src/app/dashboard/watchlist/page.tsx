"use client";

import { useState } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { WatchlistTable } from "@/components/watchlist/WatchlistTable";
import { OpenedTable } from "@/components/watchlist/OpenedTable";
import { AddWatchedIndexDialog } from "@/components/watchlist/AddWatchedIndexDialog";

type Tab = "watching" | "opened";

export default function WatchlistPage() {
  const [tab, setTab] = useState<Tab>("watching");

  return (
    <>
      <TopBar title="Watchlist" />
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30">
            <button
              onClick={() => setTab("watching")}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                tab === "watching"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Watching
            </button>
            <button
              onClick={() => setTab("opened")}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                tab === "opened"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Opened
            </button>
          </div>
          {tab === "watching" && <AddWatchedIndexDialog />}
        </div>

        <p className="text-xs text-muted-foreground font-mono">
          {tab === "watching"
            ? "Courses being monitored for open seats"
            : "Courses with available seats — enroll now or Resnipe to watch again"}
        </p>

        {tab === "watching" ? <WatchlistTable /> : <OpenedTable />}
      </div>
    </>
  );
}
