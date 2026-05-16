import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import {
  createReplayRecord,
  deleteReplayRecord,
  loadReplayDetail,
  loadReplayInbox,
  patchReplayRecord,
  queryReplayRecords,
  replaceReplayRecord,
} from "./replays";
import type {
  ApiClient,
  MetadataRecord,
  PaginatedResponse,
  ReplayPlayerRelationship,
  ReplayRecord,
} from "./types";

describe("replay workflows", () => {
  it("loads the replay inbox and curated detail from replay resource and relationship routes", async () => {
    const replay: ReplayRecord = {
      id: "a".repeat(64),
      map_name: "Post-Youth LE",
      date: "2026-01-02T00:00:00Z",
      filename: "replay.SC2Replay",
      region: "eu",
      real_length: 640,
      game_type: "1v1",
      real_type: "1v1",
      speed: "Faster",
      is_ladder: true,
      players: [
        {
          name: "zatic",
          toon_handle: "2-S2-1-123456",
          play_race: "Zerg",
          result: "Win",
        },
      ],
    };
    const metadata: MetadataRecord = {
      id: "metadata-1",
      replay: replay.id,
      description: "Macro hatch opener",
      tags: ["macro"],
      replay_summary_conversation: null,
      created_at: "2026-01-02T00:05:00Z",
      updated_at: "2026-01-02T00:05:00Z",
    };
    const players: ReplayPlayerRelationship[] = [
      {
        replay_player: replay.players[0],
        player_info: {
          id: "2-S2-1-123456",
          toon_handle: "2-S2-1-123456",
          name: "zatic",
          aliases: [],
          tags: ["known-player"],
        },
      },
    ];
    const inbox: PaginatedResponse<ReplayRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [replay],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(inbox),
      getResource: vi.fn().mockResolvedValue(replay),
      getReplayMetadata: vi.fn().mockResolvedValue(metadata),
      getReplayPlayers: vi.fn().mockResolvedValue(players),
    } as unknown as ApiClient;

    const loadedInbox = await loadReplayInbox(apiClient, { map: "Post", player: "zat" });
    const detail = await loadReplayDetail(apiClient, replay.id);

    expect(apiClient.listResource).toHaveBeenCalledWith("replays", {
      map: "Post",
      player: "zat",
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("replays", replay.id);
    expect(apiClient.getReplayMetadata).toHaveBeenCalledWith(replay.id);
    expect(apiClient.getReplayPlayers).toHaveBeenCalledWith(replay.id);
    expect(loadedInbox.docs[0]?.id).toBe(replay.id);
    expect(detail.replay.id).toBe(replay.id);
    expect(detail.metadata?.id).toBe("metadata-1");
    expect(detail.players[0]?.player_info?.id).toBe("2-S2-1-123456");
  });

  it("treats missing replay metadata as an empty curated metadata state", async () => {
    const replay: ReplayRecord = {
      id: "b".repeat(64),
      map_name: "Alcyone LE",
      date: "2026-01-03T00:00:00Z",
      filename: "replay-2.SC2Replay",
      region: "eu",
      real_length: 580,
      game_type: "1v1",
      real_type: "1v1",
      speed: "Faster",
      is_ladder: true,
      players: [],
    };
    const apiClient = {
      getResource: vi.fn().mockResolvedValue(replay),
      getReplayMetadata: vi.fn().mockRejectedValue(
        new ApiError({
          error: { code: "not_found", message: "Document not found", details: {} },
        }),
      ),
      getReplayPlayers: vi.fn().mockResolvedValue([]),
    } as unknown as ApiClient;

    const detail = await loadReplayDetail(apiClient, replay.id);

    expect(detail.metadata).toBeNull();
    expect(detail.players).toEqual([]);
  });

  it("creates, queries, patches, replaces, and deletes replay records through the typed client", async () => {
    const replay: ReplayRecord = {
      id: "c".repeat(64),
      map_name: "Crimson Court LE",
      date: "2026-01-04T00:00:00Z",
      filename: "created.SC2Replay",
      region: "eu",
      real_length: 700,
      game_type: "1v1",
      real_type: "1v1",
      speed: "Faster",
      is_ladder: true,
      players: [],
    };
    const paginated: PaginatedResponse<ReplayRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [replay],
    };
    const apiClient = {
      createResource: vi.fn().mockResolvedValue(replay),
      queryResource: vi.fn().mockResolvedValue(paginated),
      patchResource: vi.fn().mockResolvedValue({ ...replay, filename: "patched.SC2Replay" }),
      replaceResource: vi.fn().mockResolvedValue({ ...replay, filename: "replaced.SC2Replay" }),
      deleteResource: vi.fn().mockResolvedValue(undefined),
    } as unknown as ApiClient;

    await expect(createReplayRecord(apiClient, replay)).resolves.toMatchObject(replay);
    await expect(
      queryReplayRecords(apiClient, { filter: { filename: replay.filename }, docs_per_page: 10 }),
    ).resolves.toMatchObject(paginated);
    await expect(patchReplayRecord(apiClient, replay.id, { filename: "patched.SC2Replay" })).resolves.toMatchObject({
      filename: "patched.SC2Replay",
    });
    await expect(replaceReplayRecord(apiClient, replay.id, { ...replay, filename: "replaced.SC2Replay" })).resolves.toMatchObject({
      filename: "replaced.SC2Replay",
    });
    await expect(deleteReplayRecord(apiClient, replay.id)).resolves.toBeUndefined();

    expect(apiClient.createResource).toHaveBeenCalledWith("replays", replay);
    expect(apiClient.queryResource).toHaveBeenCalledWith("replays", {
      filter: { filename: replay.filename },
      docs_per_page: 10,
    });
    expect(apiClient.patchResource).toHaveBeenCalledWith("replays", replay.id, {
      filename: "patched.SC2Replay",
    });
    expect(apiClient.replaceResource).toHaveBeenCalledWith("replays", replay.id, {
      ...replay,
      filename: "replaced.SC2Replay",
    });
    expect(apiClient.deleteResource).toHaveBeenCalledWith("replays", replay.id);
  });
});