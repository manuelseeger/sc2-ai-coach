import { describe, expect, it, vi } from "vitest";

import {
  createPlayerRecord,
  deletePlayerRecord,
  loadPlayerDetail,
  loadPlayerInbox,
  loadPlayerPortraitMetadataMap,
  loadPlayerResourceDetail,
  patchPlayerRecord,
  queryPlayerRecords,
  replacePlayerRecord,
} from "./players";
import type {
  ApiClient,
  BulkPlayerPortraitMetadataRecord,
  PaginatedResponse,
  PlayerInfoRecord,
  PlayerPortraitMetadataRecord,
  ReplayRecord,
} from "./types";

describe("player workflows", () => {
  it("loads curated player detail, inbox records, and bulk portrait metadata", async () => {
    const player: PlayerInfoRecord = {
      id: "2-S2-1-123456",
      toon_handle: "2-S2-1-123456",
      name: "KnownOpponent",
      aliases: [{ name: "AliasOne", seen_on: null }],
      tags: ["ladder"],
    };
    const portraitMetadata: PlayerPortraitMetadataRecord = {
      toon_handle: player.toon_handle,
      portrait: { available: true, url: "/api/players/2-S2-1-123456/portrait" },
      portrait_constructed: {
        available: false,
        url: "/api/players/2-S2-1-123456/portrait/constructed",
      },
      aliases: [{ index: 0, name: "AliasOne", portraits: [] }],
    };
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
      players: [],
    };
    const inbox: PaginatedResponse<PlayerInfoRecord> = {
      current_page: 1,
      page_quantity: 1,
      docs_quantity: 1,
      docs: [player],
    };
    const bulk: BulkPlayerPortraitMetadataRecord = {
      items: [portraitMetadata],
    };
    const apiClient = {
      listResource: vi.fn().mockResolvedValue(inbox),
      queryResource: vi.fn().mockResolvedValue(inbox),
      getResource: vi.fn().mockResolvedValue(player),
      getPlayerAliases: vi.fn().mockResolvedValue(player.aliases),
      getPlayerPortraitMetadata: vi.fn().mockResolvedValue(portraitMetadata),
      getPlayersPortraitMetadata: vi.fn().mockResolvedValue(bulk),
      getPlayerReplays: vi.fn().mockResolvedValue({ ...inbox, docs: [replay] }),
    } as unknown as ApiClient;

    const loadedInbox = await loadPlayerInbox(apiClient, { q: "Known", tag: "ladder" });
    const query = await queryPlayerRecords(apiClient, { filter: { tags: "ladder" } });
    const detail = await loadPlayerDetail(apiClient, player.toon_handle);
    const resourceDetail = await loadPlayerResourceDetail(apiClient, player.toon_handle);
    const metadataMap = await loadPlayerPortraitMetadataMap(apiClient, [player.toon_handle]);

    expect(apiClient.listResource).toHaveBeenCalledWith("players", {
      q: "Known",
      tag: "ladder",
    });
    expect(apiClient.queryResource).toHaveBeenCalledWith("players", {
      filter: { tags: "ladder" },
    });
    expect(apiClient.getResource).toHaveBeenCalledWith("players", player.toon_handle);
    expect(apiClient.getPlayerAliases).toHaveBeenCalledWith(player.toon_handle);
    expect(apiClient.getPlayerPortraitMetadata).toHaveBeenCalledWith(player.toon_handle);
    expect(apiClient.getPlayerReplays).toHaveBeenCalledWith(player.toon_handle, {
      docs_per_page: 20,
    });
    expect(apiClient.getPlayersPortraitMetadata).toHaveBeenCalledWith([player.toon_handle]);
    expect(loadedInbox.docs[0]?.id).toBe(player.id);
    expect(query.docs_quantity).toBe(1);
    expect(detail.player.id).toBe(player.id);
    expect(detail.replays.docs[0]?.id).toBe(replay.id);
    expect(resourceDetail.name).toBe(player.name);
    expect(metadataMap[player.toon_handle]?.portrait.available).toBe(true);
  });

  it("creates, patches, replaces, and deletes player records through the typed client", async () => {
    const player: PlayerInfoRecord = {
      id: "2-S2-1-123456",
      toon_handle: "2-S2-1-123456",
      name: "KnownOpponent",
      aliases: [],
      tags: ["ladder"],
    };
    const apiClient = {
      createResource: vi.fn().mockResolvedValue(player),
      patchResource: vi.fn().mockResolvedValue({ ...player, name: "PatchedName" }),
      replaceResource: vi.fn().mockResolvedValue({ ...player, name: "ReplacedName" }),
      deleteResource: vi.fn().mockResolvedValue(undefined),
    } as unknown as ApiClient;

    await expect(createPlayerRecord(apiClient, player)).resolves.toMatchObject(player);
    await expect(patchPlayerRecord(apiClient, player.toon_handle, { name: "PatchedName" })).resolves.toMatchObject({
      name: "PatchedName",
    });
    await expect(replacePlayerRecord(apiClient, player.toon_handle, { ...player, name: "ReplacedName" })).resolves.toMatchObject({
      name: "ReplacedName",
    });
    await expect(deletePlayerRecord(apiClient, player.toon_handle)).resolves.toBeUndefined();

    expect(apiClient.createResource).toHaveBeenCalledWith("players", player);
    expect(apiClient.patchResource).toHaveBeenCalledWith("players", player.toon_handle, {
      name: "PatchedName",
    });
    expect(apiClient.replaceResource).toHaveBeenCalledWith("players", player.toon_handle, {
      ...player,
      name: "ReplacedName",
    });
    expect(apiClient.deleteResource).toHaveBeenCalledWith("players", player.toon_handle);
  });
});