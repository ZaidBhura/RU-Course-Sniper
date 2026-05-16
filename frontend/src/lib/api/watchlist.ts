import { apiClient } from "./client";
import {
  type WatchedIndexCreate,
  type WatchedIndexOut,
  WatchedIndexOutSchema,
  type WatchedIndexPatch,
} from "@/lib/schemas/watchlist";
import { z } from "zod";

export async function getWatchlist(): Promise<WatchedIndexOut[]> {
  const { data } = await apiClient.get("/watchlist/");
  return z.array(WatchedIndexOutSchema).parse(data);
}

export async function createWatchedIndex(
  body: WatchedIndexCreate
): Promise<WatchedIndexOut> {
  const { data } = await apiClient.post("/watchlist/", body);
  return WatchedIndexOutSchema.parse(data);
}

export async function patchWatchedIndex(
  id: string,
  body: WatchedIndexPatch
): Promise<WatchedIndexOut> {
  const { data } = await apiClient.patch(`/watchlist/${id}`, body);
  return WatchedIndexOutSchema.parse(data);
}

export async function deleteWatchedIndex(id: string): Promise<void> {
  await apiClient.delete(`/watchlist/${id}`);
}

export async function resnipeWatchedIndex(id: string): Promise<WatchedIndexOut> {
  const { data } = await apiClient.post(`/watchlist/${id}/resnipe`);
  return WatchedIndexOutSchema.parse(data);
}
