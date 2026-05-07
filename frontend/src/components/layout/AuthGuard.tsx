"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/hooks/useSession";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isError, isLoading } = useSession();

  useEffect(() => {
    if (isError) {
      router.replace("/auth");
    }
  }, [isError, router]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center" aria-busy="true">
        <div className="font-mono text-xs text-muted-foreground animate-pulse">
          Authenticating...
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
