import { TopBar } from "@/components/layout/TopBar";
import { ChannelList } from "@/components/channels/ChannelList";
import { AddChannelDialog } from "@/components/channels/AddChannelDialog";

export default function ChannelsPage() {
  return (
    <>
      <TopBar title="Channels" />
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground font-mono">
            Notification channels for course alerts
          </p>
          <AddChannelDialog />
        </div>
        <ChannelList />
      </div>
    </>
  );
}
