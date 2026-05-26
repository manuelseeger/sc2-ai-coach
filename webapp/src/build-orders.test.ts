import { describe, expect, it } from "vitest";

import { summarizeBuildOrder, summarizeOpening } from "./build-orders";
import type { ReplayBuildOrderEntry } from "./types";

describe("build order presentation", () => {
  it("keeps each build order event as its own row", () => {
    const entries: ReplayBuildOrderEntry[] = [
      { frame: 15.2, time: "0:00", name: "Drone", supply: 12, is_worker: true },
      { frame: 247.2, time: "0:11", name: "Drone", supply: 13, is_worker: true },
      { frame: 387, time: "0:17", name: "Extractor", supply: 14 },
      { frame: 402, time: "0:18", name: "Drone", supply: 15, is_worker: true },
      {
        frame: 620,
        time: "0:27",
        name: "Nexus",
        supply: 16,
        is_chronoboosted: true,
      },
    ];

    expect(summarizeBuildOrder(entries)).toEqual([
      {
        id: "step-0-Drone-0:00",
        time: "0:00",
        supply: "12",
        build: "Drone",
        isChronoboosted: false,
      },
      {
        id: "step-1-Drone-0:11",
        time: "0:11",
        supply: "13",
        build: "Drone",
        isChronoboosted: false,
      },
      {
        id: "step-2-Extractor-0:17",
        time: "0:17",
        supply: "14",
        build: "Extractor",
        isChronoboosted: false,
      },
      {
        id: "step-3-Drone-0:18",
        time: "0:18",
        supply: "15",
        build: "Drone",
        isChronoboosted: false,
      },
      {
        id: "step-4-Nexus-0:27",
        time: "0:27",
        supply: "16",
        build: "Nexus",
        isChronoboosted: true,
      },
    ]);
  });

  it("derives a concise opener summary from non-worker steps", () => {
    const entries: ReplayBuildOrderEntry[] = [
      { frame: 15.2, time: "0:00", name: "SCV", supply: 12, is_worker: true },
      { frame: 400, time: "0:17", name: "SupplyDepot", supply: 14 },
      { frame: 525, time: "0:23", name: "Barracks", supply: 16 },
      { frame: 770, time: "0:34", name: "Refinery", supply: 17 },
      { frame: 980, time: "0:43", name: "OrbitalCommand", supply: 19 },
      { frame: 1120, time: "0:49", name: "CommandCenter", supply: 20 },
    ];

    expect(summarizeOpening(entries, 4)).toBe(
      "14 Supply Depot -> 16 Barracks -> 17 Refinery -> 19 Orbital Command",
    );
  });
});