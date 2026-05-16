"use client";

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
import { Badge } from "@/components/ui/badge";
import { LoadingRow } from "@/components/shared/LoadingRow";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { IndexNumber } from "@/components/shared/IndexNumber";
import { useWatchlist, useResnipe } from "@/lib/hooks/useWatchlist";
import { formatTimestamp, formatSemesterCode } from "@/lib/utils/formatters";
import type { WatchedIndexOut } from "@/lib/schemas/watchlist";

const WEBREG_BASE =
  "https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas";

function buildWebregUrl(semesterCode: string, indexNumber: number): string {
  return `${WEBREG_BASE}&semesterSelection=${semesterCode}&indexList=${indexNumber}`;
}

function OpenedRow({ item }: { item: WatchedIndexOut }) {
  const { mutate: resnipe, isPending } = useResnipe();

  function handleResnipe() {
    resnipe(item.id, {
      onSuccess: () => toast.success(`Index ${item.index_number} moved back to Watching`),
      onError: () => toast.error("Failed to resnipe"),
    });
  }

  return (
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
      <TableCell className="text-xs text-muted-foreground font-mono">
        {formatTimestamp(item.updated_at)}
      </TableCell>
      <TableCell>
        <a
          href={buildWebregUrl(item.semester_code, item.index_number)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-mono text-primary underline underline-offset-2 hover:opacity-80"
        >
          Enroll in WebReg
        </a>
      </TableCell>
      <TableCell>
        <Button
          variant="outline"
          size="sm"
          onClick={handleResnipe}
          disabled={isPending}
          className="h-7 text-xs font-mono"
        >
          Resnipe
        </Button>
      </TableCell>
    </TableRow>
  );
}

export function OpenedTable() {
  const { data: allItems, isLoading, error } = useWatchlist();
  const items = allItems?.filter((i) => i.status === "opened");

  return (
    <div className="space-y-4">
      <ErrorBanner error={error as Error | null} />

      {isLoading ? (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Index", "Course", "Semester", "Opened", "WebReg", ""].map((h) => (
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
          title="No opened courses"
          description="Courses move here when a seat opens and you've been notified."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Index", "Course", "Semester", "Opened", "WebReg", ""].map((h) => (
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
              <OpenedRow key={item.id} item={item} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
