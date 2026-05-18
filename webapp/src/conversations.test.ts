import { describe, expect, it, vi } from "vitest";

import {
  appendConversationItem,
  createConversationRecord,
  deleteConversationRecord,
  getConversationInboxState,
  loadConversationDetail,
  loadConversationInbox,
  patchConversationRecord,
  queryConversationRecords,
  replaceConversationRecord,
  resetConversationInboxState,
  setConversationInboxState,
} from "./conversations";
import type {
  ApiClient,
  ConversationItemRecord,
  ConversationRecord,
  PaginatedResponse,
} from "./types";

describe("conversation workflows", () => {
  it("loads the curated inbox and detail through conversation routes", async () => {
    const conversation: ConversationRecord = {
      id: "conversation-1",
      session: "session-1",
      trigger: "wake",
      status: "active",
      created_at: "2026-01-02T00:00:00Z",
      item_count: 2,
      last_item_at: "2026-01-02T00:03:00Z",
      replay_id: "replay-1",
      metadata: {},
    };
    const items: ConversationItemRecord[] = [
      {
        id: "item-1",
        conversation: conversation.id,
        session: conversation.session,
        type: "message",
        order: 0,
        created_at: "2026-01-02T00:00:00Z",
        role: "user",
        content: [{ text: "hello" }],
        call_id: null,
        name: null,
        arguments: null,
        output: null,
        response_id: null,
        response_model: null,
        status: null,
        raw_item: null,
        source: null,
        included_in_context: true,
        metadata: {},
      },
    ];
    const inbox: PaginatedResponse<ConversationRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [conversation],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(inbox),
      getResource: vi.fn().mockResolvedValue(conversation),
      getConversationItems: vi.fn().mockResolvedValue(items),
      getConversationResponses: vi.fn().mockResolvedValue([]),
    } as unknown as ApiClient;

    const loadedInbox = await loadConversationInbox(apiClient, {
      trigger: "wake",
      status: "active",
    });
    const detail = await loadConversationDetail(apiClient, conversation.id);

    expect(apiClient.listResource).toHaveBeenCalledWith("conversations", {
      trigger: "wake",
      status: "active",
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("conversations", conversation.id);
    expect(apiClient.getConversationItems).toHaveBeenCalledWith(conversation.id);
    expect(apiClient.getConversationResponses).toHaveBeenCalledWith(conversation.id);
    expect(loadedInbox.docs[0]?.id).toBe(conversation.id);
    expect(detail.items[0]?.id).toBe("item-1");
  });

  it("creates, queries, patches, replaces, deletes, and appends through the typed client", async () => {
    const conversation: ConversationRecord = {
      id: "conversation-2",
      session: null,
      trigger: "repl",
      status: "active",
      created_at: "2026-01-03T00:00:00Z",
      item_count: 1,
      last_item_at: "2026-01-03T00:00:00Z",
      metadata: { scope: "test" },
    };
    const paginated: PaginatedResponse<ConversationRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [conversation],
    };
    const item: ConversationItemRecord = {
      id: "item-2",
      conversation: conversation.id,
      session: null,
      type: "message",
      order: 1,
      created_at: "2026-01-03T00:02:00Z",
      role: "assistant",
      content: [{ text: "reply" }],
      call_id: null,
      name: null,
      arguments: null,
      output: null,
      response_id: null,
      response_model: null,
      status: null,
      raw_item: null,
      source: null,
      included_in_context: true,
      metadata: {},
    };
    const apiClient = {
      createResource: vi.fn().mockResolvedValue(conversation),
      queryResource: vi.fn().mockResolvedValue(paginated),
      patchResource: vi.fn().mockResolvedValue({ ...conversation, status: "closed" }),
      replaceResource: vi.fn().mockResolvedValue({ ...conversation, status: "closed" }),
      deleteResource: vi.fn().mockResolvedValue(undefined),
      createConversationItem: vi.fn().mockResolvedValue(item),
    } as unknown as ApiClient;

    await expect(createConversationRecord(apiClient, conversation)).resolves.toMatchObject(conversation);
    await expect(
      queryConversationRecords(apiClient, {
        filter: { trigger: conversation.trigger },
        docs_per_page: 10,
      }),
    ).resolves.toMatchObject(paginated);
    await expect(
      patchConversationRecord(apiClient, conversation.id, { status: "closed" }),
    ).resolves.toMatchObject({ status: "closed" });
    await expect(
      replaceConversationRecord(apiClient, conversation.id, { ...conversation, status: "closed" }),
    ).resolves.toMatchObject({ status: "closed" });
    await expect(deleteConversationRecord(apiClient, conversation.id)).resolves.toBeUndefined();
    await expect(
      appendConversationItem(apiClient, conversation.id, {
        conversation: conversation.id,
        type: "message",
        role: "assistant",
        content: [{ text: "reply" }],
      }),
    ).resolves.toMatchObject({ id: "item-2" });

    expect(apiClient.createResource).toHaveBeenCalledWith("conversations", conversation);
    expect(apiClient.queryResource).toHaveBeenCalledWith("conversations", {
      filter: { trigger: conversation.trigger },
      docs_per_page: 10,
    });
    expect(apiClient.patchResource).toHaveBeenCalledWith("conversations", conversation.id, {
      status: "closed",
    });
    expect(apiClient.replaceResource).toHaveBeenCalledWith(
      "conversations",
      conversation.id,
      { ...conversation, status: "closed" },
    );
    expect(apiClient.deleteResource).toHaveBeenCalledWith("conversations", conversation.id);
    expect(apiClient.createConversationItem).toHaveBeenCalledWith(conversation.id, {
      conversation: conversation.id,
      type: "message",
      role: "assistant",
      content: [{ text: "reply" }],
    });
  });

  it("persists inbox state across SPA navigation only", () => {
    resetConversationInboxState();

    setConversationInboxState({
      params: {
        trigger: "wake",
        status: "active",
        current_page: 2,
      },
      selectedConversationId: "conversation-9",
    });

    expect(getConversationInboxState()).toEqual({
      params: {
        trigger: "wake",
        status: "active",
        current_page: 2,
      },
      selectedConversationId: "conversation-9",
    });

    resetConversationInboxState();

    expect(getConversationInboxState()).toEqual({
      params: {
        sort: "-created_at",
        current_page: 1,
        docs_per_page: 25,
      },
      selectedConversationId: null,
    });
  });
});