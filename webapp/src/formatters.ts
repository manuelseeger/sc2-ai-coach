const triggerLabels: Record<string, string> = {
  wake: "Wake word",
  repl: "REPL",
  game_start: "Game start",
  new_replay: "New replay",
  twitch_chat: "Twitch chat",
  twitch_follow: "Twitch follow",
  twitch_raid: "Twitch raid",
  cast_replay: "Cast replay",
  replay_summary: "Replay summary",
};

const okTriggers = new Set(["game_start", "new_replay", "cast_replay", "replay_summary"]);
const accentTriggers = new Set(["twitch_chat", "twitch_follow", "twitch_raid"]);
const replayRaceClasses: Record<string, string> = {
  Terran: "race--t",
  Protoss: "race--p",
  Zerg: "race--z",
  Random: "race--r",
};

const replayRaceAbbreviations: Record<string, string> = {
  Terran: "T",
  Protoss: "P",
  Zerg: "Z",
  Random: "R",
};

const replayRaceTagClasses: Record<string, string> = {
  Terran: "tag--race-t",
  Protoss: "tag--race-p",
  Zerg: "tag--race-z",
  Random: "tag--race-r",
};

export function formatDate(value: string | null | undefined, fallback = "—"): string {
  if (!value) {
    return fallback;
  }

  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    hour12: false,
  });
}

export function formatUsd(value: number, digits = 4): string {
  return `$${value.toFixed(digits)}`;
}

export function formatDuration(seconds: number | null | undefined, fallback = "—"): string {
  if (seconds == null) {
    return fallback;
  }

  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${remainder}`;
}

export function triggerLabel(value: string): string {
  return triggerLabels[value] ?? value;
}

export function triggerClass(value: string): string {
  if (okTriggers.has(value)) {
    return "tag--ok";
  }

  if (accentTriggers.has(value)) {
    return "tag--accent";
  }

  if (value === "repl") {
    return "tag--purple";
  }

  if (value === "wake") {
    return "tag--warn";
  }

  return "";
}

export function replayRaceClass(race: string): string {
  return replayRaceClasses[race] ?? "race--r";
}

export function replayRaceAbbr(race: string): string {
  return replayRaceAbbreviations[race] ?? race[0] ?? "?";
}

export function replayRaceTagClass(race: string): string {
  return replayRaceTagClasses[race] ?? "";
}

export function replayResultClass(result: string): string {
  if (result === "Win") {
    return "tag--ok";
  }

  if (result === "Loss") {
    return "tag--warn";
  }

  return "";
}