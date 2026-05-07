"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/utils/queryKeys";
import { getChannels, createChannel, deleteChannel } from "@/lib/api/channels";
import type { ChannelCreate } from "@/lib/schemas/channels";

export function useChannels() {
  return useQuery({
    queryKey: queryKeys.channels,
    queryFn: getChannels,
    staleTime: 30_000,
  });
}

export function useCreateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ChannelCreate) => createChannel(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.channels }),
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteChannel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.channels }),
  });
}
