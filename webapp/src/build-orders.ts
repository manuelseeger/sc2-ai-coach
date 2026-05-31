import type { ReplayBuildOrderEntry } from "./types";
import { canonicalUnitName } from "./unit-name-aliases";

export interface BuildOrderDisplayStep {
  id: string;
  time: string;
  supply: string;
  build: string;
  isChronoboosted: boolean;
}

export function summarizeBuildOrder(entries: ReplayBuildOrderEntry[] | null | undefined): BuildOrderDisplayStep[] {
  if (!entries?.length) {
    return [];
  }

  return entries
    .filter((entry): entry is ReplayBuildOrderEntry => Boolean(entry))
    .map((entry, index) => ({
      id: `step-${index}-${entry.name}-${entry.time}`,
      time: entry.time,
      supply: String(entry.supply),
      build: canonicalUnitName(entry.name),
      isChronoboosted: Boolean(entry.is_chronoboosted),
    }));
}

export function summarizeOpening(entries: ReplayBuildOrderEntry[] | null | undefined, limit = 5): string {
  if (!entries?.length) {
    return "";
  }

  return entries
    .filter((entry) => !entry.is_worker)
    .slice(0, limit)
    .map((entry) => `${entry.supply} ${canonicalUnitName(entry.name)}`)
    .join(" -> ");
}