import { TopBar } from "@/components/layout/TopBar";
import { LogsTable } from "@/components/logs/LogsTable";

export default function LogsPage() {
  return (
    <>
      <TopBar title="Logs" />
      <div className="p-6 max-w-5xl">
        <p className="text-xs text-muted-foreground font-mono mb-4">
          Notification history — last 100 events
        </p>
        <LogsTable />
      </div>
    </>
  );
}
