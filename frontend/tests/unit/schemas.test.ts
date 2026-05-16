import { describe, it, expect } from "vitest";
import { LoginSchema, RegisterSchema } from "@/lib/schemas/auth";
import { WatchedIndexCreateSchema } from "@/lib/schemas/watchlist";
import { ChannelCreateSchema } from "@/lib/schemas/channels";
import { NotificationLogOutSchema } from "@/lib/schemas/logs";

describe("LoginSchema", () => {
  it("rejects empty email", () => {
    expect(LoginSchema.safeParse({ email: "", password: "secret" }).success).toBe(false);
  });
  it("rejects invalid email format", () => {
    expect(LoginSchema.safeParse({ email: "not-an-email", password: "secret" }).success).toBe(false);
  });
  it("rejects empty password", () => {
    expect(LoginSchema.safeParse({ email: "a@b.com", password: "" }).success).toBe(false);
  });
  it("accepts valid credentials", () => {
    expect(LoginSchema.safeParse({ email: "a@b.com", password: "hunter2" }).success).toBe(true);
  });
});

describe("RegisterSchema", () => {
  it("rejects password under 8 chars", () => {
    const r = RegisterSchema.safeParse({ email: "a@b.com", password: "short" });
    expect(r.success).toBe(false);
  });
  it("rejects password over 128 chars", () => {
    const r = RegisterSchema.safeParse({ email: "a@b.com", password: "x".repeat(129) });
    expect(r.success).toBe(false);
  });
  it("accepts valid 8-char password", () => {
    expect(RegisterSchema.safeParse({ email: "a@b.com", password: "12345678" }).success).toBe(true);
  });
});

describe("WatchedIndexCreateSchema", () => {
  it("rejects index 0", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 0 });
    expect(r.success).toBe(false);
  });
  it("rejects index 100000", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 100000 });
    expect(r.success).toBe(false);
  });
  it("accepts boundary index 1", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 1 });
    expect(r.success).toBe(true);
  });
  it("accepts boundary index 99999", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 99999 });
    expect(r.success).toBe(true);
  });
  it("rejects semester_code with 4 digits", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 123, semester_code: "1234" });
    expect(r.success).toBe(false);
  });
  it("accepts semester_code 92026", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 123, semester_code: "92026" });
    expect(r.success).toBe(true);
  });
  it("defaults semester_code to 92026", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 123 });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.semester_code).toBe("92026");
  });
  it("rejects label over 200 chars", () => {
    const r = WatchedIndexCreateSchema.safeParse({ index_number: 123, label: "x".repeat(201) });
    expect(r.success).toBe(false);
  });
});

describe("ChannelCreateSchema — Discord", () => {
  it("rejects non-Discord URLs", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "discord",
      credential: { webhook_url: "https://example.com/hook" },
    });
    expect(r.success).toBe(false);
  });
  it("rejects non-URL strings", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "discord",
      credential: { webhook_url: "not-a-url" },
    });
    expect(r.success).toBe(false);
  });
  it("accepts valid Discord webhook URL", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "discord",
      credential: { webhook_url: "https://discord.com/api/webhooks/123/abc" },
    });
    expect(r.success).toBe(true);
  });
});

describe("ChannelCreateSchema — Pushover", () => {
  it("rejects missing token", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "pushover",
      credential: { token: "", user_key: "key" },
    });
    expect(r.success).toBe(false);
  });
  it("rejects missing user_key", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "pushover",
      credential: { token: "tok", user_key: "" },
    });
    expect(r.success).toBe(false);
  });
  it("accepts valid pushover credentials", () => {
    const r = ChannelCreateSchema.safeParse({
      channel_type: "pushover",
      credential: { token: "mytoken", user_key: "mykey" },
    });
    expect(r.success).toBe(true);
  });
});

describe("NotificationLogOutSchema", () => {
  const validLog = {
    id: "00000000-0000-0000-0000-000000000001",
    index_number: 12345,
    semester_code: "12026",
    channel_type: "discord",
    event_type: "open_notify",
    delivery_status: "sent",
    course_subject: null,
    course_number: null,
    course_title: null,
    webreg_url: null,
    created_at: "2026-01-01T00:00:00Z",
  };
  it("accepts valid log with all null optionals", () => {
    expect(NotificationLogOutSchema.safeParse(validLog).success).toBe(true);
  });
  it("accepts valid log with course info", () => {
    const r = NotificationLogOutSchema.safeParse({
      ...validLog,
      course_subject: "CS",
      course_number: "111",
      course_title: "Intro to CS",
      webreg_url: "https://webreg.rutgers.edu/whatever",
    });
    expect(r.success).toBe(true);
  });
  it("rejects invalid delivery_status", () => {
    const r = NotificationLogOutSchema.safeParse({ ...validLog, delivery_status: "pending" });
    expect(r.success).toBe(false);
  });
  it("rejects invalid event_type", () => {
    const r = NotificationLogOutSchema.safeParse({ ...validLog, event_type: "unknown" });
    expect(r.success).toBe(false);
  });
});
