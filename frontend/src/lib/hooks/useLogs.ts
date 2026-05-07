"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/utils/queryKeys";
import { getLogs } from "@/lib/api/logs";

export function useLogs() {
  return useQuery({
    queryKey: queryKeys.logs,
    queryFn: getLogs,
    staleTime: 0,
  });
}
