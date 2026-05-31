import { describe, expect, it } from "vitest";

import { prepareDisplay } from "./json-display";

describe("prepareDisplay", () => {
  it("returns isJson=true for a plain JSON object string", () => {
    const result = prepareDisplay('{"a":1,"b":"two"}');
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(true);
    expect(result.parsed).toEqual({ a: 1, b: "two" });
  });

  it("returns isJson=true for a plain JSON array string", () => {
    const result = prepareDisplay('[1,2,3]');
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(true);
    expect(result.parsed).toEqual([1, 2, 3]);
  });

  it("returns isJson=true for an already-parsed object", () => {
    const result = prepareDisplay({ x: 1 });
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(false);
    expect(result.parsed).toEqual({ x: 1 });
  });

  it("returns isJson=true for an already-parsed array", () => {
    const result = prepareDisplay([10, 20]);
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(false);
    expect(result.parsed).toEqual([10, 20]);
  });

  it("recursively unwraps a once-encoded JSON object string", () => {
    // A string whose JSON.parse yields another JSON string that decodes to an object
    const inner = JSON.stringify({ query: "test" });
    const encoded = JSON.stringify(inner);
    const result = prepareDisplay(encoded);
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(true);
    expect(result.parsed).toEqual({ query: "test" });
  });

  it("recursively unwraps a twice-encoded JSON object string", () => {
    const inner = JSON.stringify({ op: "eq" });
    const twice = JSON.stringify(JSON.stringify(inner));
    const result = prepareDisplay(twice);
    expect(result.isJson).toBe(true);
    expect(result.isParsed).toBe(true);
    expect(result.parsed).toEqual({ op: "eq" });
  });

  it("stops recursive unwrapping at max depth and returns plain text", () => {
    // Build a 6-deep encoding chain (exceeds depth 5)
    let v: string = "deep";
    for (let i = 0; i < 6; i++) v = JSON.stringify(v);
    const result = prepareDisplay(v);
    // Should not throw; should return something sensible
    expect(result.isJson).toBe(false);
  });

  it("decodes a JSON string scalar and returns plain text", () => {
    const result = prepareDisplay('"hello world"');
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(true);
    expect(result.displayText).toBe("hello world");
  });

  it("decodes escaped quotes in a JSON string scalar", () => {
    const result = prepareDisplay('"say \\"hello\\""');
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(true);
    expect(result.displayText).toBe('say "hello"');
  });

  it("leaves a plain text string alone", () => {
    const result = prepareDisplay("just plain text");
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(false);
    expect(result.displayText).toBe("just plain text");
  });

  it("returns empty displayText for an empty string", () => {
    const result = prepareDisplay("");
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(false);
    expect(result.displayText).toBe("");
  });

  it("leaves an invalid JSON string alone", () => {
    const result = prepareDisplay("{invalid json}");
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(false);
    expect(result.displayText).toBe("{invalid json}");
  });

  it("returns isJson=false for a JSON number string", () => {
    const result = prepareDisplay("42");
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(true);
    expect(result.displayText).toBe("42");
  });

  it("returns isJson=false for a JSON boolean string", () => {
    const result = prepareDisplay("true");
    expect(result.isJson).toBe(false);
    expect(result.isParsed).toBe(true);
    expect(result.displayText).toBe("true");
  });

  it("handles null input", () => {
    const result = prepareDisplay(null);
    expect(result.isJson).toBe(false);
    expect(result.parsed).toBeNull();
    expect(result.displayText).toBe("null");
  });

  it("handles undefined input", () => {
    const result = prepareDisplay(undefined);
    expect(result.isJson).toBe(false);
    expect(result.displayText).toBe("");
  });
});
