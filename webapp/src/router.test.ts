import { describe, expect, it } from "vitest";

import { routes } from "./routes";

describe("router", () => {
  it("registers dedicated session, conversation, replay, player, and metadata workflow routes", () => {
    expect(routes.map((route) => route.path)).toContain("/sessions");
    expect(routes.map((route) => route.path)).toContain("/sessions/:sessionId");
    expect(routes.map((route) => route.path)).toContain("/conversations");
    expect(routes.map((route) => route.path)).toContain("/conversations/:conversationId");
    expect(routes.map((route) => route.path)).toContain("/replays");
    expect(routes.map((route) => route.path)).toContain("/replays/:replayId");
    expect(routes.map((route) => route.path)).toContain("/players");
    expect(routes.map((route) => route.path)).toContain("/players/:toonHandle");
    expect(routes.map((route) => route.path)).toContain("/resources/conversations");
    expect(routes.map((route) => route.path)).toContain("/resources/conversations/new");
    expect(routes.map((route) => route.path)).toContain("/resources/conversations/:conversationId");
    expect(routes.map((route) => route.path)).toContain("/resources/replays");
    expect(routes.map((route) => route.path)).toContain("/resources/replays/new");
    expect(routes.map((route) => route.path)).toContain("/resources/replays/:replayId");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata/new");
    expect(routes.map((route) => route.path)).toContain("/resources/metadata/:metadataId");
    expect(routes.map((route) => route.path)).toContain("/resources/players");
    expect(routes.map((route) => route.path)).toContain("/resources/players/new");
    expect(routes.map((route) => route.path)).toContain("/resources/players/:toonHandle");
    expect(routes.map((route) => route.path)).toContain("/resources/conversation-items");
    expect(routes.map((route) => route.path)).toContain("/resources/conversation-items/:recordId");
    expect(routes.map((route) => route.path)).toContain("/resources/responses");
    expect(routes.map((route) => route.path)).toContain("/resources/responses/:recordId");
  });
});