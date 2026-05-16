import { describe, expect, it, vi } from "vitest";

import {
  createMetadataRecord,
  deleteMetadataRecord,
  loadMetadataDetail,
  loadMetadataInbox,
  patchMetadataRecord,
  queryMetadataRecords,
  replaceMetadataRecord,
} from "./metadata";
import type { ApiClient, MetadataRecord, PaginatedResponse } from "./types";

describe("metadata workflows", () => {
  it("loads list, detail, and advanced query from the metadata resource family", async () => {
    const payload: PaginatedResponse<MetadataRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [
        {
          id: "metadata-1",
          replay: "a".repeat(64),
          description: "Macro opener",
          tags: ["macro"],
          replay_summary_conversation: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(payload),
      queryResource: vi.fn().mockResolvedValue(payload),
      getResource: vi.fn().mockResolvedValue(payload.docs[0]),
    } as unknown as ApiClient;

    const inbox = await loadMetadataInbox(apiClient, { tag: "macro", has_summary: true });
    const detail = await loadMetadataDetail(apiClient, "metadata-1");
    const query = await queryMetadataRecords(apiClient, {
      filter: { tags: "macro" },
      sort: { updated_at: -1 },
      current_page: 1,
      docs_per_page: 10,
    });

    expect(apiClient.listResource).toHaveBeenCalledWith("metadata", {
      tag: "macro",
      has_summary: true,
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("metadata", "metadata-1");
    expect(apiClient.queryResource).toHaveBeenCalledWith("metadata", {
      filter: { tags: "macro" },
      sort: { updated_at: -1 },
      current_page: 1,
      docs_per_page: 10,
    });
    expect(inbox.docs[0]?.id).toBe("metadata-1");
    expect(detail.id).toBe("metadata-1");
    expect(query.docs_quantity).toBe(1);
  });

  it("creates, patches, replaces, and deletes metadata through the typed client", async () => {
    const created: MetadataRecord = {
      id: "metadata-1",
      replay: "a".repeat(64),
      description: "Created",
      tags: ["macro"],
      replay_summary_conversation: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    const apiClient = {
      createResource: vi.fn().mockResolvedValue(created),
      patchResource: vi.fn().mockResolvedValue({ ...created, description: "Patched" }),
      replaceResource: vi
        .fn()
        .mockResolvedValue({ ...created, description: "Replaced", tags: ["replacement"] }),
      deleteResource: vi.fn().mockResolvedValue(undefined),
    } as unknown as ApiClient;

    const createBody = { replay: created.replay, description: "Created", tags: ["macro"] };
    const patchBody = { description: "Patched" };
    const replaceBody = { ...created, description: "Replaced", tags: ["replacement"] };

    await expect(createMetadataRecord(apiClient, createBody)).resolves.toMatchObject(created);
    await expect(patchMetadataRecord(apiClient, created.id, patchBody)).resolves.toMatchObject({
      description: "Patched",
    });
    await expect(replaceMetadataRecord(apiClient, created.id, replaceBody)).resolves.toMatchObject(
      {
        description: "Replaced",
      },
    );
    await expect(deleteMetadataRecord(apiClient, created.id)).resolves.toBeUndefined();

    expect(apiClient.createResource).toHaveBeenCalledWith("metadata", createBody);
    expect(apiClient.patchResource).toHaveBeenCalledWith("metadata", created.id, patchBody);
    expect(apiClient.replaceResource).toHaveBeenCalledWith(
      "metadata",
      created.id,
      replaceBody,
    );
    expect(apiClient.deleteResource).toHaveBeenCalledWith("metadata", created.id);
  });
});