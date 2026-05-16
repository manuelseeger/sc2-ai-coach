import { describe, expect, it } from "vitest";

import { routes } from "./routes";

describe("router", () => {
  it("registers dedicated session and metadata workflow routes", () => {
    expect(routes.map((route) => route.path)).toContain("/sessions");
    expect(routes.map((route) => route.path)).toContain("/sessions/:sessionId");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata/new");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata/:metadataId");
  });
});