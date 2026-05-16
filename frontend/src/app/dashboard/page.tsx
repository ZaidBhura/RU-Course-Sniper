import { TopBar } from "@/components/layout/TopBar";
import { StatsBar } from "@/components/dashboard/StatsBar";
import { RecentActivityFeed } from "@/components/dashboard/RecentActivityFeed";

export default function DashboardPage() {
  return (
    <>
      <TopBar title="Dashboard" />
      <div className="p-6 space-y-6">
        <StatsBar />
        <RecentActivityFeed />
      </div>
    </>
  );
}
