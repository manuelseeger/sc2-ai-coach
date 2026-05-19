import { describe, expect, it, vi } from "vitest";

import {
  loadReadOnlyResourceDetail,
  loadReadOnlyResourceInbox,
  lookupResponseRecord,
  queryReadOnlyResourceRecords,
} from "./read-only-resources";
import type {
  ApiClient,
  ConversationItemRecord,
  PaginatedResponse,
  ResponseRecord,
  SessionRecord,
} from "./types";

describe("read-only resource workflows", () => {
  it("loads list, detail, and query reads for conversation items", async () => {
    const item: ConversationItemRecord = {
      id: "item-1",
      conversation: "conversation-1",
      session: "session-1",
      type: "message",
      order: 1,
      created_at: "2026-01-01T00:00:00Z",
      role: "assistant",
      content: [{ text: "Hello" }],
      call_id: null,
      name: null,
      arguments: null,
      output: null,
      response_id: null,
      response_model: null,
      status: null,
      raw_item: { kind: "assistant-trace" },
      source: "test",
      metadata: { lane: "raw" },
    };
    const payload: PaginatedResponse<ConversationItemRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [item],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(payload),
      queryResource: vi.fn().mockResolvedValue(payload),
      getResource: vi.fn().mockResolvedValue(item),
    } as unknown as ApiClient;

    const inbox = await loadReadOnlyResourceInbox(apiClient, "conversation-items", {
      conversation: "conversation-1",
    });
    const detail = await loadReadOnlyResourceDetail(apiClient, "conversation-items", "item-1");
    const query = await queryReadOnlyResourceRecords(apiClient, "conversation-items", {
      filter: { response_id: "resp-1" },
      sort: { created_at: -1 },
      current_page: 1,
      docs_per_page: 10,
    });

    expect(apiClient.listResource).toHaveBeenCalledWith("conversation-items", {
      conversation: "conversation-1",
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("conversation-items", "item-1");
    expect(apiClient.queryResource).toHaveBeenCalledWith("conversation-items", {
      filter: { response_id: "resp-1" },
      sort: { created_at: -1 },
      current_page: 1,
      docs_per_page: 10,
    });
    expect(inbox.docs[0]?.id).toBe("item-1");
    expect(detail.id).toBe("item-1");
    expect(query.docs_quantity).toBe(1);
  });

  it("loads response detail and alternate-key response-id lookups", async () => {
    const record: ResponseRecord = {
      id: "response-record-1",
      conversation: "conversation-1",
      session: "session-1",
      response_id: "resp-lookup-1",
      model: "gpt-5.4",
      status: "completed",
      streamed: false,
      created_at: "2026-01-01T00:00:00Z",
      input_tokens: 10,
      cached_tokens: 0,
      output_tokens: 5,
      total_tokens: 15,
      input_cost: 0.1,
      cached_input_cost: 0,
      output_cost: 0.2,
      total_cost: 0.3,
      raw_usage: { input_tokens: 10 },
      metadata: { lane: "audit" },
    };
    const apiClient = {
      getResource: vi.fn().mockResolvedValue(record),
      getResponseByResponseId: vi.fn().mockResolvedValue(record),
    } as unknown as ApiClient;

    const detail = await loadReadOnlyResourceDetail(apiClient, "responses", record.id);
    const lookedUp = await lookupResponseRecord(apiClient, "resp-lookup-1");

    expect(apiClient.getResource).toHaveBeenCalledWith("responses", record.id);
    expect(apiClient.getResponseByResponseId).toHaveBeenCalledWith("resp-lookup-1");
    expect(detail.id).toBe(record.id);
    expect(lookedUp.response_id).toBe("resp-lookup-1");
  });

  it("loads session list, detail, and query reads for generic session resources", async () => {
    const session: SessionRecord = {
      id: "session-1",
      conversations: ["conversation-1", "conversation-2"],
      current_conversation: "conversation-2",
      twitch_conversation: null,
      ai_backend: "OpenAI",
      session_date: "2026-01-01T00:00:00Z",
      completion_pricing: 0.2,
      prompt_pricing: 0.1,
      cached_prompt_pricing: 0,
      total_input_tokens: 10,
      total_cached_tokens: 0,
      total_output_tokens: 5,
      total_tokens: 15,
      total_cost: 0.3,
    };
    const payload: PaginatedResponse<SessionRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [session],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(payload),
      queryResource: vi.fn().mockResolvedValue(payload),
      getResource: vi.fn().mockResolvedValue(session),
    } as unknown as ApiClient;

    const inbox = await loadReadOnlyResourceInbox(apiClient, "sessions", {
      sort: "-session_date",
    });
    const detail = await loadReadOnlyResourceDetail(apiClient, "sessions", "session-1");
    const query = await queryReadOnlyResourceRecords(apiClient, "sessions", {
      filter: { ai_backend: "OpenAI" },
      sort: { session_date: -1 },
      current_page: 1,
      docs_per_page: 10,
    });

    expect(apiClient.listResource).toHaveBeenCalledWith("sessions", {
      sort: "-session_date",
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("sessions", "session-1");
    expect(apiClient.queryResource).toHaveBeenCalledWith("sessions", {
      filter: { ai_backend: "OpenAI" },
      sort: { session_date: -1 },
      current_page: 1,
      docs_per_page: 10,
    });
    expect(inbox.docs[0]?.id).toBe("session-1");
    expect(detail.id).toBe("session-1");
    expect(query.docs_quantity).toBe(1);
  });
});