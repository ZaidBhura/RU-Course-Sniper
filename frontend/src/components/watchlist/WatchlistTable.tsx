"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { LoadingRow } from "@/components/shared/LoadingRow";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { IndexNumber } from "@/components/shared/IndexNumber";
import {
  useWatchlist,
  usePatchWatchedIndex,
  useDeleteWatchedIndex,
} from "@/lib/hooks/useWatchlist";
import { formatTimestamp, formatSemesterCode } from "@/lib/utils/formatters";
import type { WatchedIndexOut } from "@/lib/schemas/watchlist";
import { Trash2 } from "lucide-react";

function WatchedIndexRow({ item }: { item: WatchedIndexOut }) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { mutate: patch, isPending: patching } = usePatchWatchedIndex();
  const { mutate: del, isPending: deleting } = useDeleteWatchedIndex();

  function toggleActive(checked: boolean) {
    patch(
      { id: item.id, body: { is_active: checked } },
      {
        onSuccess: () =>
          toast.success(checked ? "Index activated" : "Index deactivated"),
        onError: () => toast.error("Failed to update"),
      }
    );
  }

  function handleDelete() {
    del(item.id, {
      onSuccess: () => {
        toast.success(`Index ${item.index_number} removed`);
        setDeleteOpen(false);
      },
      onError: () => toast.error("Failed to remove"),
    });
  }

  return (
    <>
      <TableRow className="border-border hover:bg-accent/30 transition-colors">
        <TableCell className="font-mono">
          <IndexNumber value={item.index_number} />
        </TableCell>
        <TableCell className="text-sm text-muted-foreground">
          {item.label
            ? <span>{item.label}</span>
            : item.course_name
              ? <span>{item.course_name}</span>
              : <span className="text-muted-foreground/50 italic">—</span>}
        </TableCell>
        <TableCell>
          <Badge
            variant="outline"
            className="font-mono text-xs border-border text-muted-foreground"
          >
            {formatSemesterCode(item.semester_code)}
          </Badge>
        </TableCell>
        <TableCell>
          <Switch
            checked={item.is_active}
            onCheckedChange={toggleActive}
            disabled={patching}
            aria-label={`Toggle ${item.index_number} active`}
          />
        </TableCell>
        <TableCell className="text-xs text-muted-foreground font-mono">
          {formatTimestamp(item.created_at)}
        </TableCell>
        <TableCell>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDeleteOpen(true)}
            className="text-muted-foreground hover:text-destructive h-7 w-7 p-0"
            aria-label={`Delete index ${item.index_number}`}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
          </Button>
        </TableCell>
      </TableRow>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Remove from watchlist?"
        description={`Index ${item.index_number}${item.label ? ` (${item.label})` : ""} will stop being monitored.`}
        onConfirm={handleDelete}
        loading={deleting}
        confirmLabel="Remove"
      />
    </>
  );
}

export function WatchlistTable() {
  const { data: allItems, isLoading, error } = useWatchlist();
  const items = allItems?.filter((i) => i.status === "watching");

  return (
    <div className="space-y-4">
      <ErrorBanner error={error as Error | null} />

      {isLoading ? (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Index", "Course", "Semester", "Active", "Added", ""].map((h) => (
                <TableHead key={h} className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {[0, 1, 2].map((i) => <LoadingRow key={i} cols={6} />)}
          </TableBody>
        </Table>
      ) : items?.length === 0 ? (
        <EmptyState
          title="No courses being watched"
          description="Add a course index to start monitoring for open seats."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Index", "Course", "Semester", "Active", "Added", ""].map((h) => (
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
            {items?.map((item) => (
              <WatchedIndexRow key={item.id} item={item} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
