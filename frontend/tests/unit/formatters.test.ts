import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  formatSemesterCode,
  formatEventType,
  formatDeliveryStatus,
  formatChannelType,
  padIndex,
  formatTimestamp,
} from "@/lib/utils/formatters";

describe("formatSemesterCode", () => {
  it("formats Spring 2026", () => expect(formatSemesterCode("12026")).toBe("Spring 2026"));
  it("formats Fall with 9 prefix", () => expect(formatSemesterCode("92025")).toBe("Fall 2025"));
  it("formats Summer with 7 prefix", () => expect(formatSemesterCode("72026")).toBe("Summer 2026"));
  it("returns raw code if not 5 digits", () => expect(formatSemesterCode("123")).toBe("123"));
});

describe("formatEventType", () => {
  it("maps open_notify", () => expect(formatEventType("open_notify")).toBe("Course Opened"));
  it("maps close_reset", () => expect(formatEventType("close_reset")).toBe("Course Closed"));
});

describe("formatDeliveryStatus", () => {
  it("returns green for sent", () => {
    const r = formatDeliveryStatus("sent");
    expect(r.label).toBe("Sent");
    expect(r.colorClass).toContain("00c896");
  });
  it("returns destructive for failed", () => {
    const r = formatDeliveryStatus("failed");
    expect(r.label).toBe("Failed");
    expect(r.colorClass).toContain("destructive");
  });
  it("returns muted for skipped", () => {
    const r = formatDeliveryStatus("skipped");
    expect(r.label).toBe("Skipped");
    expect(r.colorClass).toContain("muted");
  });
});

describe("formatChannelType", () => {
  it("formats discord", () => expect(formatChannelType("discord")).toBe("Discord"));
  it("formats pushover", () => expect(formatChannelType("pushover")).toBe("Pushover"));
});

describe("padIndex", () => {
  it("pads 1 to 00001", () => expect(padIndex(1)).toBe("00001"));
  it("pads 99999 unchanged", () => expect(padIndex(99999)).toBe("99999"));
  it("pads 123 to 00123", () => expect(padIndex(123)).toBe("00123"));
});

describe("formatTimestamp", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-01T12:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());

  it("returns 'just now' for < 1 min ago", () => {
    const iso = new Date("2026-06-01T11:59:30Z").toISOString();
    expect(formatTimestamp(iso)).toBe("just now");
  });
  it("returns Xm ago for recent minutes", () => {
    const iso = new Date("2026-06-01T11:55:00Z").toISOString();
    expect(formatTimestamp(iso)).toBe("5m ago");
  });
  it("returns Xh ago for recent hours", () => {
    const iso = new Date("2026-06-01T10:00:00Z").toISOString();
    expect(formatTimestamp(iso)).toBe("2h ago");
  });
  it("returns Xd ago for recent days", () => {
    const iso = new Date("2026-05-29T12:00:00Z").toISOString();
    expect(formatTimestamp(iso)).toBe("3d ago");
  });
});
