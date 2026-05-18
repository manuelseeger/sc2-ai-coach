import type { ConversationItemRecord } from "./types";

export interface ConnectorMeta {
  lane: number;
  role: "call-start" | "through" | "result-end";
}

const MAX_LANES = 3;

/**
 * Compute connector metadata for each conversation item.
 *
 * Returns one array per item. Each inner array contains one entry per connector
 * that covers that item's position in the transcript. An empty array means the
 * item is not part of any connection (orphan Tool Result or unrelated item).
 *
 * Pairing rules:
 * - Match function_call_output to function_call by call_id.
 * - Nearest preceding call wins on duplicate call_ids.
 * - Falls back to nearest following call when no preceding match exists.
 *
 * Lane assignment:
 * - Connections sorted by callIdx (call order) for determinism.
 * - Lowest free lane wins; falls back to lane 0 when all MAX_LANES are occupied.
 */
export function computeConnectors(items: ConversationItemRecord[]): ConnectorMeta[][] {
  interface Connection {
    callIdx: number;
    resultIdx: number;
    lane: number;
  }

  const connections: Connection[] = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type !== "function_call_output" || !item.call_id) continue;

    const callId = item.call_id;

    // Search backwards for nearest preceding function_call with same call_id
    let matchIdx = -1;
    for (let j = i - 1; j >= 0; j--) {
      if (items[j].type === "function_call" && items[j].call_id === callId) {
        matchIdx = j;
        break;
      }
    }

    // Fall back to nearest following call when no preceding match exists
    if (matchIdx === -1) {
      for (let j = i + 1; j < items.length; j++) {
        if (items[j].type === "function_call" && items[j].call_id === callId) {
          matchIdx = j;
          break;
        }
      }
    }

    if (matchIdx === -1) continue; // orphan – no connector

    connections.push({
      callIdx: Math.min(matchIdx, i),
      resultIdx: Math.max(matchIdx, i),
      lane: 0,
    });
  }

  // Sort by callIdx for deterministic lane assignment by call order
  connections.sort((a, b) => a.callIdx - b.callIdx);

  for (let c = 0; c < connections.length; c++) {
    const conn = connections[c];
    const occupiedLanes = new Set<number>();

    for (let k = 0; k < c; k++) {
      const other = connections[k];
      // Two ranges overlap when neither ends before the other starts
      if (other.callIdx <= conn.resultIdx && conn.callIdx <= other.resultIdx) {
        occupiedLanes.add(other.lane);
      }
    }

    // Assign the lowest free lane; fall back to 0 if all MAX_LANES are occupied
    conn.lane = 0;
    for (let lane = 0; lane < MAX_LANES; lane++) {
      if (!occupiedLanes.has(lane)) {
        conn.lane = lane;
        break;
      }
    }
  }

  // Build per-item result arrays
  const result: ConnectorMeta[][] = items.map(() => []);

  for (const conn of connections) {
    for (let i = conn.callIdx; i <= conn.resultIdx; i++) {
      const role: ConnectorMeta["role"] =
        i === conn.callIdx ? "call-start"
        : i === conn.resultIdx ? "result-end"
        : "through";
      result[i].push({ lane: conn.lane, role });
    }
  }

  return result;
}
