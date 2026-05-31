import { describe, expect, it } from "vitest";

import { createApiClient } from "./api";
import { adminAreas, resourceRegistry } from "./route-registry";
import { routes } from "./routes";

describe("webapp bootstrap", () => {
  it("exposes a fixed admin registry and typed API shell", () => {
    expect(resourceRegistry.map((resource) => resource.name)).toEqual([
      "replays",
      "metadata",
      "players",
      "sessions",
      "conversations",
      "conversation-items",
      "responses",
    ]);

    expect(adminAreas.map((area) => area.id)).toContain("workspace");
    expect(adminAreas.map((area) => area.id)).toContain("health");
    expect(adminAreas.map((area) => area.id)).toContain("players-review");

    const client = createApiClient();

    expect(client).toMatchObject({
      getHealth: expect.any(Function),
      listResource: expect.any(Function),
      getResource: expect.any(Function),
      getSessionConversations: expect.any(Function),
      getConversationItems: expect.any(Function),
      getResponseByResponseId: expect.any(Function),
      getPlayerAliases: expect.any(Function),
      getPlayerPortraitMetadata: expect.any(Function),
      getPlayerReplays: expect.any(Function),
      getTools: expect.any(Function),
    });
  });
});