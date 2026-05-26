import iconMap from "./unit-icon-map.json";
import { canonicalUnitName } from "./unit-name-aliases";

const map = iconMap as Record<string, string>;

export type StructureColor = "blue" | "red";

export function getUnitIconUrl(name: string, color: StructureColor = "blue"): string | null {
  const canonical = canonicalUnitName(name);
  if (!canonical) return null;
  const raw = map[canonical];
  if (!raw) return null;
  return `/assets/${raw.replace("{color}", color)}`;
}
