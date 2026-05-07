"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { useChannels, useDeleteChannel } from "@/lib/hooks/useChannels";
import { formatTimestamp, formatChannelType } from "@/lib/utils/formatters";
import type { ChannelOut } from "@/lib/schemas/channels";

function ChannelCard({ channel }: { channel: ChannelOut }) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const { mutate: del, isPending } = useDeleteChannel();

  function handleDelete() {
    del(channel.id, {
      onSuccess: () => {
        toast.success(`${formatChannelType(channel.channel_type)} channel removed`);
        setConfirmOpen(false);
      },
      onError: () => toast.error("Failed to remove channel"),
    });
  }

  return (
    <>
      <div className="flex items-center justify-between rounded-sm border border-border bg-card px-4 py-3">
        <div className="flex items-center gap-4">
          <span className="font-mono text-lg select-none" aria-hidden>
            {channel.channel_type === "discord" ? "💬" : "📳"}
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">
              {formatChannelType(channel.channel_type)}
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              Added {formatTimestamp(channel.created_at)} ·{" "}
              <span className={channel.is_active ? "text-[#00c896]" : "text-muted-foreground"}>
                {channel.is_active ? "Active" : "Inactive"}
              </span>
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setConfirmOpen(true)}
          className="text-muted-foreground hover:text-destructive h-7 w-7 p-0"
          aria-label={`Remove ${formatChannelType(channel.channel_type)} channel`}
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </Button>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`Remove ${formatChannelType(channel.channel_type)} channel?`}
        description="This will stop sending notifications to this channel."
        onConfirm={handleDelete}
        loading={isPending}
        confirmLabel="Remove"
      />
    </>
  );
}

export function ChannelList() {
  const { data: channels, isLoading, error } = useChannels();

  return (
    <div className="space-y-3">
      <ErrorBanner error={error as Error | null} />

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-16 bg-muted animate-pulse rounded-sm" aria-busy="true" />
          ))}
        </div>
      ) : channels?.length === 0 ? (
        <EmptyState
          title="No channels configured"
          description="Add a Discord webhook or Pushover credentials to receive notifications."
        />
      ) : (
        channels?.map((c) => <ChannelCard key={c.id} channel={c} />)
      )}
    </div>
  );
}
