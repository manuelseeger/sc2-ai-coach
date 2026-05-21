import { describe, expect, it } from "vitest";

import { renderMessage } from "./message-rendering";

describe("renderMessage", () => {
  it("plain Markdown returns a single html block with rendered markup", () => {
    const blocks = renderMessage("Hello **world**");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("html");
    if (blocks[0].kind === "html") {
      expect(blocks[0].html).toContain("<strong>world</strong>");
    }
  });

  it("empty string returns no blocks", () => {
    expect(renderMessage("")).toHaveLength(0);
    expect(renderMessage("   ")).toHaveLength(0);
  });

  it("fenced json block with valid object returns a single json block", () => {
    const blocks = renderMessage('```json\n{"a":1}\n```');
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("json");
    if (blocks[0].kind === "json") {
      expect(blocks[0].value).toEqual({ a: 1 });
    }
  });

  it("fenced json block with valid array returns a json block", () => {
    const blocks = renderMessage("```json\n[1, 2, 3]\n```");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("json");
    if (blocks[0].kind === "json") {
      expect(blocks[0].value).toEqual([1, 2, 3]);
    }
  });

  it("Markdown before and after a json block yields three ordered blocks", () => {
    const text = "Before\n\n```json\n{\"x\":2}\n```\n\nAfter";
    const blocks = renderMessage(text);
    expect(blocks).toHaveLength(3);
    expect(blocks[0].kind).toBe("html");
    expect(blocks[1].kind).toBe("json");
    expect(blocks[2].kind).toBe("html");
    if (blocks[1].kind === "json") expect(blocks[1].value).toEqual({ x: 2 });
  });

  it("multiple json blocks maintain insertion order", () => {
    const text = '```json\n[1,2]\n```\n\n```json\n{"b":3}\n```';
    const blocks = renderMessage(text);
    const jsonBlocks = blocks.filter((b) => b.kind === "json");
    expect(jsonBlocks).toHaveLength(2);
    if (jsonBlocks[0].kind === "json") expect(jsonBlocks[0].value).toEqual([1, 2]);
    if (jsonBlocks[1].kind === "json") expect(jsonBlocks[1].value).toEqual({ b: 3 });
  });

  it("malformed json fence falls back to an html code block", () => {
    const blocks = renderMessage("```json\n{invalid}\n```");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("html");
    if (blocks[0].kind === "html") {
      expect(blocks[0].html).toContain("<code");
      expect(blocks[0].html).toContain("{invalid}");
    }
  });

  it("non-json code fence renders as html", () => {
    const blocks = renderMessage('```python\nprint("hi")\n```');
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("html");
    if (blocks[0].kind === "html") {
      expect(blocks[0].html).toContain("<code");
      expect(blocks[0].html).toContain("print");
    }
  });

  it("bare JSON object (no fences) is treated as plain Markdown text, not a json block", () => {
    const blocks = renderMessage('{"no":"fences"}');
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("html");
  });

  it("content with multiple paragraphs produces a single html block containing both", () => {
    const blocks = renderMessage("Part one\n\nPart two");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("html");
    if (blocks[0].kind === "html") {
      expect(blocks[0].html).toContain("Part one");
      expect(blocks[0].html).toContain("Part two");
    }
  });
});
