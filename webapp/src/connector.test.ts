import { describe, expect, it } from "vitest";

import { computeConnectors } from "./connector";
import type { ConversationItemRecord } from "./types";

function makeItem(overrides: Partial<ConversationItemRecord> = {}): ConversationItemRecord {
  return {
    id: Math.random().toString(36).slice(2),
    conversation: "conv1",
    session: null,
    type: "message",
    order: 0,
    created_at: new Date().toISOString(),
    role: "user",
    content: [],
    call_id: null,
    name: null,
    arguments: null,
    output: null,
    response_id: null,
    response_model: null,
    status: null,
    raw_item: null,
    source: null,
    metadata: null,
    ...overrides,
  };
}

function makeCall(call_id: string, overrides: Partial<ConversationItemRecord> = {}): ConversationItemRecord {
  return makeItem({ type: "function_call", call_id, name: "QueryReplayDB", role: null, ...overrides });
}

function makeResult(call_id: string, overrides: Partial<ConversationItemRecord> = {}): ConversationItemRecord {
  return makeItem({ type: "function_call_output", call_id, output: "some output", role: null, ...overrides });
}

describe("computeConnectors", () => {
  it("returns empty arrays for items with no tool calls", () => {
    const items = [
      makeItem({ type: "message", role: "user" }),
      makeItem({ type: "message", role: "assistant" }),
    ];
    const result = computeConnectors(items);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual([]);
    expect(result[1]).toEqual([]);
  });

  it("connects adjacent function_call and function_call_output", () => {
    const items = [makeCall("c1"), makeResult("c1")];
    const result = computeConnectors(items);
    expect(result[0]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[1]).toEqual([{ lane: 0, role: "result-end" }]);
  });

  it("connects non-adjacent call and result with through items in between", () => {
    const items = [
      makeCall("c1"),
      makeItem({ type: "message", role: "assistant" }),
      makeResult("c1"),
    ];
    const result = computeConnectors(items);
    expect(result[0]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[1]).toEqual([{ lane: 0, role: "through" }]);
    expect(result[2]).toEqual([{ lane: 0, role: "result-end" }]);
  });

  it("returns empty array for orphan result with no matching call", () => {
    const items = [
      makeItem({ type: "message", role: "user" }),
      makeResult("unknown-id"),
    ];
    const result = computeConnectors(items);
    expect(result[0]).toEqual([]);
    expect(result[1]).toEqual([]);
  });

  it("returns empty array for result with null call_id", () => {
    const items = [
      makeCall("c1"),
      makeItem({ type: "function_call_output", call_id: null }),
    ];
    const result = computeConnectors(items);
    expect(result[1]).toEqual([]);
  });

  it("nearest preceding call wins when duplicate call_ids exist", () => {
    const items = [
      makeCall("dup"),  // 0 – farther preceding
      makeItem({ type: "message", role: "assistant" }),  // 1
      makeCall("dup"),  // 2 – nearest preceding
      makeResult("dup"),  // 3
    ];
    const result = computeConnectors(items);
    // index 0 is NOT part of any connection
    expect(result[0]).toEqual([]);
    // index 1 is NOT a through item (connection is 2→3, not 0→3)
    expect(result[1]).toEqual([]);
    expect(result[2]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[3]).toEqual([{ lane: 0, role: "result-end" }]);
  });

  it("connects to nearest following call when no preceding call exists", () => {
    const items = [
      makeResult("c1"),  // 0 – result before its call
      makeCall("c1"),    // 1 – following call
    ];
    const result = computeConnectors(items);
    // callIdx=0 (result position), resultIdx=1 (call position)
    expect(result[0]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[1]).toEqual([{ lane: 0, role: "result-end" }]);
  });

  it("assigns different lanes to overlapping connector ranges", () => {
    // c1: indices 0→4, c2: indices 2→6
    const items = [
      makeCall("c1"),   // 0
      makeItem(),       // 1
      makeCall("c2"),   // 2
      makeItem(),       // 3
      makeResult("c1"), // 4
      makeItem(),       // 5
      makeResult("c2"), // 6
    ];
    const result = computeConnectors(items);

    // c1 gets lane 0 (first by call order)
    expect(result[0]).toEqual([{ lane: 0, role: "call-start" }]);
    // Index 4 is result-end for c1 AND through for c2 (c2 spans 2→6)
    expect(result[4]).toContainEqual({ lane: 0, role: "result-end" });
    expect(result[4]).toContainEqual({ lane: 1, role: "through" });

    // c2 gets lane 1 (lane 0 occupied when starting at index 2)
    expect(result[2]).toContainEqual({ lane: 1, role: "call-start" });
    expect(result[6]).toEqual([{ lane: 1, role: "result-end" }]);

    // Index 3 is through for both connections
    expect(result[3]).toContainEqual({ lane: 0, role: "through" });
    expect(result[3]).toContainEqual({ lane: 1, role: "through" });
  });

  it("falls back to lane 0 when all 3 lanes are occupied (generic rail fallback)", () => {
    // 4 overlapping connections → 4th falls back to lane 0
    const items = [
      makeCall("c1"),   // 0
      makeCall("c2"),   // 1
      makeCall("c3"),   // 2
      makeCall("c4"),   // 3
      makeResult("c1"), // 4
      makeResult("c2"), // 5
      makeResult("c3"), // 6
      makeResult("c4"), // 7
    ];
    const result = computeConnectors(items);
    // Lanes assigned in call order: c1→0, c2→1, c3→2, c4→0 (fallback)
    expect(result[0]).toContainEqual({ lane: 0, role: "call-start" });
    expect(result[1]).toContainEqual({ lane: 1, role: "call-start" });
    expect(result[2]).toContainEqual({ lane: 2, role: "call-start" });
    expect(result[3]).toContainEqual({ lane: 0, role: "call-start" });
  });

  it("handles multiple non-overlapping connections each on lane 0", () => {
    const items = [
      makeCall("c1"),   // 0
      makeResult("c1"), // 1
      makeCall("c2"),   // 2
      makeResult("c2"), // 3
    ];
    const result = computeConnectors(items);
    expect(result[0]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[1]).toEqual([{ lane: 0, role: "result-end" }]);
    expect(result[2]).toEqual([{ lane: 0, role: "call-start" }]);
    expect(result[3]).toEqual([{ lane: 0, role: "result-end" }]);
  });
});
