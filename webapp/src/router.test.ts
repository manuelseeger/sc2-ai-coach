import { describe, expect, it } from "vitest";

import { routes } from "./routes";

describe("router", () => {
  it("registers dedicated session inbox and detail routes", () => {
    expect(routes.map((route) => route.path)).toContain("/sessions");
    expect(routes.map((route) => route.path)).toContain("/sessions/:sessionId");
  });
});