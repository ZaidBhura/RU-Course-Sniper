"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession } from "@/lib/hooks/useSession";
import {
  LayoutDashboard,
  BookOpen,
  Bell,
  ScrollText,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/watchlist", label: "Watchlist", icon: BookOpen, exact: false },
  { href: "/dashboard/channels", label: "Channels", icon: Bell, exact: false },
  { href: "/dashboard/logs", label: "Logs", icon: ScrollText, exact: false },
];

function NavItem({
  href,
  label,
  icon: Icon,
  exact,
}: {
  href: string;
  label: string;
  icon: React.ElementType;
  exact: boolean;
}) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 text-sm transition-colors",
        "border-l-2 border-transparent",
        "hover:text-foreground hover:border-muted-foreground",
        isActive
          ? "text-foreground border-l-primary"
          : "text-muted-foreground"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {label}
    </Link>
  );
}

export function Sidebar() {
  const { data: session } = useSession();

  return (
    <aside
      className="hidden md:flex w-56 shrink-0 flex-col border-r border-border bg-sidebar h-full"
      aria-label="Main navigation"
    >
      <div className="flex items-center h-14 px-4 border-b border-border">
        <span className="font-mono text-sm font-semibold tracking-widest text-primary">
          RU
        </span>
        <span className="font-mono text-sm font-semibold text-foreground ml-1">
          SNIPER
        </span>
      </div>

      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {navItems.map((item) => (
          <NavItem key={item.href} {...item} />
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border">
        <p className="text-xs text-muted-foreground font-mono truncate">
          {session?.email ?? "—"}
        </p>
      </div>
    </aside>
  );
}
