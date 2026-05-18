import { describe, expect, it } from "vitest";

import { formatDate, formatDuration, formatUsd, replayRaceAbbr, replayRaceClass, replayRaceTagClass, replayResultClass, triggerClass, triggerLabel } from "./formatters";

describe("formatters", () => {
  it("formats missing dates with the provided fallback", () => {
    expect(formatDate(null, "None")).toBe("None");
    expect(formatDate(undefined)).toBe("—");
  });

  it("maps trigger labels to readable copy", () => {
    expect(triggerLabel("wake")).toBe("Wake word");
    expect(triggerLabel("custom_trigger")).toBe("custom_trigger");
  });

  it("formats costs as usd strings", () => {
    expect(formatUsd(1.23456)).toBe("$1.2346");
    expect(formatUsd(1.2, 2)).toBe("$1.20");
  });

  it("formats durations and replay race helpers", () => {
    expect(formatDuration(125)).toBe("2:05");
    expect(formatDuration(null)).toBe("—");
    expect(replayRaceClass("Protoss")).toBe("race--p");
    expect(replayRaceAbbr("Zerg")).toBe("Z");
    expect(replayRaceTagClass("Terran")).toBe("tag--race-t");
    expect(replayResultClass("Win")).toBe("tag--ok");
  });

  it("maps trigger classes to tag variants", () => {
    expect(triggerClass("new_replay")).toBe("tag--ok");
    expect(triggerClass("twitch_chat")).toBe("tag--accent");
    expect(triggerClass("repl")).toBe("tag--purple");
    expect(triggerClass("unknown")).toBe("");
  });
});