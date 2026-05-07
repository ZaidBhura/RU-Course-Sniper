"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut, ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useSession } from "@/lib/hooks/useSession";
import { toast } from "sonner";

interface TopBarProps {
  title?: string;
}

export function TopBar({ title }: TopBarProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: session } = useSession();

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      qc.clear();
      router.push("/auth");
      router.refresh();
    } catch {
      toast.error("Logout failed. Please try again.");
    }
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border px-6">
      {title && (
        <h1 className="text-sm font-medium text-foreground">{title}</h1>
      )}
      <div className="ml-auto">
        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground rounded-sm px-2 py-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label="User menu"
          >
            <span className="font-mono max-w-[160px] truncate">
              {session?.email ?? "—"}
            </span>
            <ChevronDown className="h-3 w-3" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="text-destructive focus:text-destructive gap-2"
            >
              <LogOut className="h-4 w-4" aria-hidden />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
