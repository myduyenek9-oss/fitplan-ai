import { describe, expect, it } from "vitest";
import { formatRecordTime, getRecordDisplayTimestamp } from "./record-time";

describe("formatRecordTime", () => {
  it("uses the creation minute for an older AI record rounded to the hour", () => {
    expect(formatRecordTime({
      loggedAt: "2026-07-22T19:00:00+08:00",
      createdAt: "2026-07-22T19:43:26+08:00",
      sourceText: "evening meal",
      preferCreatedAtForRoundedAiTime: true,
    })).toBe("19:43");
  });

  it("keeps an explicitly supplied minute", () => {
    expect(formatRecordTime({
      loggedAt: "2026-07-22T08:35:00+08:00",
      createdAt: "2026-07-22T19:43:26+08:00",
      sourceText: "ate at 8:35",
      preferCreatedAtForRoundedAiTime: true,
    })).toBe("08:35");
  });


  it("keeps an AI-estimated clock time when the user supplied a time-of-day phrase", () => {
    expect(formatRecordTime({
      loggedAt: "2026-07-22T12:00:00+08:00",
      createdAt: "2026-07-22T19:43:26+08:00",
      sourceText: "中午吃了一碗饭",
      preferCreatedAtForRoundedAiTime: true,
    })).toBe("12:00");
  });

  it("places an earlier time-of-day record before a later record", () => {
    const roundedAiRecord = getRecordDisplayTimestamp({
      loggedAt: "2026-07-22T19:00:00+08:00",
      createdAt: "2026-07-22T19:43:26+08:00",
      sourceText: "晚餐加了一杯牛奶",
      preferCreatedAtForRoundedAiTime: true,
    });
    const explicitRecord = getRecordDisplayTimestamp({ loggedAt: "2026-07-22T19:21:00+08:00" });
    expect(roundedAiRecord).toBeLessThan(explicitRecord);
  });
});
