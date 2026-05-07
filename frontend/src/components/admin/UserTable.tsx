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
import { Switch } from "@/components/ui/switch";
import { LoadingRow } from "@/components/shared/LoadingRow";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBanner } from "@/components/shared/ErrorBanner";
import { useAdminUsers, usePatchUser } from "@/lib/hooks/useAdmin";
import { useSession } from "@/lib/hooks/useSession";
import { formatTimestamp } from "@/lib/utils/formatters";
import type { UserOut } from "@/lib/schemas/user";

function UserRow({ user, currentUserId }: { user: UserOut; currentUserId?: string }) {
  const { mutate: patch } = usePatchUser();
  const isSelf = user.id === currentUserId;

  function toggle(field: "is_active" | "is_superuser", value: boolean) {
    patch(
      { id: user.id, body: { [field]: value } },
      {
        onSuccess: () => toast.success("User updated"),
        onError: () => toast.error("Failed to update user"),
      }
    );
  }

  return (
    <TableRow className="border-border hover:bg-accent/30 transition-colors">
      <TableCell className="text-sm font-mono text-foreground">{user.email}</TableCell>
      <TableCell>
        <Switch
          checked={user.is_active}
          onCheckedChange={(v) => toggle("is_active", v)}
          disabled={isSelf}
          aria-label={`Toggle ${user.email} active`}
        />
      </TableCell>
      <TableCell>
        <Switch
          checked={user.is_superuser}
          onCheckedChange={(v) => toggle("is_superuser", v)}
          disabled={isSelf}
          aria-label={`Toggle ${user.email} superuser`}
        />
      </TableCell>
      <TableCell className="text-xs text-muted-foreground font-mono">
        {formatTimestamp(user.created_at)}
      </TableCell>
      {isSelf && (
        <TableCell className="text-xs text-muted-foreground font-mono">(you)</TableCell>
      )}
    </TableRow>
  );
}

export function UserTable() {
  const { data: users, isLoading, error } = useAdminUsers();
  const { data: session } = useSession();

  return (
    <div className="space-y-4">
      <ErrorBanner error={error as Error | null} />

      {isLoading ? (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Email", "Active", "Superuser", "Joined", ""].map((h) => (
                <TableHead key={h} className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {[0, 1, 2].map((i) => <LoadingRow key={i} cols={5} />)}
          </TableBody>
        </Table>
      ) : users?.length === 0 ? (
        <EmptyState title="No users found" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border">
              {["Email", "Active", "Superuser", "Joined", ""].map((h) => (
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
            {users?.map((user) => (
              <UserRow key={user.id} user={user} currentUserId={session?.id} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
