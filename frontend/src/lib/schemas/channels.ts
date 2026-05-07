import { z } from "zod";

export const DiscordCredentialSchema = z.object({
  webhook_url: z
    .string()
    .url("Must be a valid URL")
    .startsWith(
      "https://discord.com/api/webhooks/",
      "Must be a Discord webhook URL"
    ),
});

export const PushoverCredentialSchema = z.object({
  token: z.string().min(1, "Token is required"),
  user_key: z.string().min(1, "User key is required"),
});

export const ChannelCreateDiscordSchema = z.object({
  channel_type: z.literal("discord"),
  credential: DiscordCredentialSchema,
});

export const ChannelCreatePushoverSchema = z.object({
  channel_type: z.literal("pushover"),
  credential: PushoverCredentialSchema,
});

export const ChannelCreateSchema = z.discriminatedUnion("channel_type", [
  ChannelCreateDiscordSchema,
  ChannelCreatePushoverSchema,
]);

export const ChannelOutSchema = z.object({
  id: z.string().uuid(),
  channel_type: z.enum(["discord", "pushover"]),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type ChannelCreate = z.infer<typeof ChannelCreateSchema>;
export type ChannelOut = z.infer<typeof ChannelOutSchema>;
