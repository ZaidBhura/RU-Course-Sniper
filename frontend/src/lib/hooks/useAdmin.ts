"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/utils/queryKeys";
import {
  adminGetUsers,
  adminPatchUser,
  adminGetWatchlists,
  adminGetLogs,
} from "@/lib/api/admin";
import type { UserPatch } from "@/lib/schemas/user";

export function useAdminUsers() {
  return useQuery({
    queryKey: queryKeys.adminUsers,
    queryFn: adminGetUsers,
    staleTime: 30_000,
  });
}

export function usePatchUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserPatch }) =>
      adminPatchUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.adminUsers }),
  });
}

export function useAdminWatchlists() {
  return useQuery({
    queryKey: queryKeys.adminWatchlists,
    queryFn: adminGetWatchlists,
    staleTime: 30_000,
  });
}

export function useAdminLogs() {
  return useQuery({
    queryKey: queryKeys.adminLogs,
    queryFn: adminGetLogs,
    staleTime: 0,
  });
}
