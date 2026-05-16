import { describe, expect, it, vi } from "vitest";

import type { ApiClient, PaginatedResponse, SessionRecord } from "./types";
import { loadSessionDetail, loadSessionInbox } from "./sessions";

describe("session workflows", () => {
  it("loads the session inbox from the sessions resource family", async () => {
    const payload: PaginatedResponse<SessionRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [
        {
          id: "session-1",
          ai_backend: "OpenAI",
          session_date: "2026-01-02T00:00:00",
          conversations: ["conversation-1"],
          current_conversation: "conversation-1",
          twitch_conversation: null,
          completion_pricing: 0.3,
          prompt_pricing: 0.4,
          cached_prompt_pricing: 0,
          total_input_tokens: 10,
          total_cached_tokens: 0,
          total_output_tokens: 5,
          total_tokens: 15,
          total_cost: 0.5,
        },
      ],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(payload),
    } as unknown as ApiClient;

    const result = await loadSessionInbox(apiClient);

    expect(apiClient.listResource).toHaveBeenCalledWith("sessions");
    expect(result.docs[0]?.id).toBe("session-1");
  });

  it("loads a session detail together with its linked conversations", async () => {
    const session: SessionRecord = {
      id: "session-1",
      ai_backend: "OpenAI",
      session_date: "2026-01-02T00:00:00",
      conversations: ["conversation-1"],
      current_conversation: "conversation-1",
      twitch_conversation: null,
      completion_pricing: 0.3,
      prompt_pricing: 0.4,
      cached_prompt_pricing: 0,
      total_input_tokens: 10,
      total_cached_tokens: 0,
      total_output_tokens: 5,
      total_tokens: 15,
      total_cost: 0.5,
    };
    const conversations = [
      {
        id: "conversation-1",
        session: "session-1",
        trigger: "wake",
        status: "active",
        created_at: "2026-01-02T00:05:00",
        title: "Ladder match",
        item_count: 3,
        last_item_at: "2026-01-02T00:10:00",
        metadata: {},
      },
    ];
    const apiClient = {
      getResource: vi.fn().mockResolvedValue(session),
      getSessionConversations: vi.fn().mockResolvedValue(conversations),
    } as unknown as ApiClient;

    const result = await loadSessionDetail(apiClient, "session-1");

    expect(apiClient.getResource).toHaveBeenCalledWith("sessions", "session-1");
    expect(apiClient.getSessionConversations).toHaveBeenCalledWith("session-1");
    expect(result.session.id).toBe("session-1");
    expect(result.conversations[0]?.id).toBe("conversation-1");
  });
});