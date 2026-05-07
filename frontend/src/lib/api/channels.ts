import { apiClient } from "./client";
import {
  ChannelCreate,
  ChannelOut,
  ChannelOutSchema,
} from "@/lib/schemas/channels";
import { z } from "zod";

export async function getChannels(): Promise<ChannelOut[]> {
  const { data } = await apiClient.get("/channels/");
  return z.array(ChannelOutSchema).parse(data);
}

export async function createChannel(body: ChannelCreate): Promise<ChannelOut> {
  const { data } = await apiClient.post("/channels/", body);
  return ChannelOutSchema.parse(data);
}

export async function deleteChannel(id: string): Promise<void> {
  await apiClient.delete(`/channels/${id}`);
}
