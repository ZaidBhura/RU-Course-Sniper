"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/utils/queryKeys";
import {
  getWatchlist,
  createWatchedIndex,
  patchWatchedIndex,
  deleteWatchedIndex,
} from "@/lib/api/watchlist";
import type { WatchedIndexCreate, WatchedIndexPatch } from "@/lib/schemas/watchlist";

export function useWatchlist() {
  return useQuery({
    queryKey: queryKeys.watchlist,
    queryFn: getWatchlist,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useCreateWatchedIndex() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WatchedIndexCreate) => createWatchedIndex(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.watchlist }),
  });
}

export function usePatchWatchedIndex() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WatchedIndexPatch }) =>
      patchWatchedIndex(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.watchlist }),
  });
}

export function useDeleteWatchedIndex() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWatchedIndex(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.watchlist }),
  });
}
