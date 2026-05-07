"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/utils/queryKeys";
import { UserOut, UserOutSchema } from "@/lib/schemas/user";

async function fetchSession(): Promise<UserOut> {
  let res = await fetch("/api/auth/me", { credentials: "same-origin" });

  if (res.status === 401) {
    const refreshRes = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "same-origin",
    });
    if (!refreshRes.ok) throw new Error("Not authenticated");
    res = await fetch("/api/auth/me", { credentials: "same-origin" });
  }

  if (!res.ok) throw new Error("Not authenticated");
  return UserOutSchema.parse(await res.json());
}

export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: fetchSession,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
