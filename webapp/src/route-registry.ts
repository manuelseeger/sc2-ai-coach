import type { AdminArea, ResourceDefinition } from "./types";

export const resourceRegistry: ResourceDefinition[] = [
  {
    name: "replays",
    label: "Replays",
    description: "Browse and manage game replays.",
    writable: true,
  },
  {
    name: "metadata",
    label: "Metadata",
    description: "Notes and annotations attached to replays.",
    writable: true,
  },
  {
    name: "players",
    label: "Players",
    description: "Known players, aliases, and profiles.",
    writable: true,
  },
  {
    name: "sessions",
    label: "Sessions",
    description: "Coaching session summaries.",
    writable: false,
  },
  {
    name: "conversations",
    label: "Conversations",
    description: "Coaching conversations and transcripts.",
    writable: true,
  },
  {
    name: "conversation-items",
    label: "Conversation Items",
    description: "Individual messages from all conversations.",
    writable: false,
  },
  {
    name: "responses",
    label: "Responses",
    description: "AI response logs and usage records.",
    writable: false,
  },
];

export const adminAreas: AdminArea[] = [
  {
    id: "workspace",
    label: "Workspace",
    description: "Overview of all available sections.",
    path: "/",
  },
  {
    id: "sessions-review",
    label: "Sessions",
    description: "Recent coaching sessions.",
    path: "/sessions",
  },
  {
    id: "conversations-review",
    label: "Conversations",
    description: "Review coaching conversations and transcripts.",
    path: "/conversations",
  },
  {
    id: "replays-review",
    label: "Replays",
    description: "Browse replays with linked annotations and players.",
    path: "/replays",
  },
  {
    id: "players-review",
    label: "Players",
    description: "Browse players with aliases and replay history.",
    path: "/players",
  },
  {
    id: "health",
    label: "Health",
    description: "Check service health and connectivity.",
    path: "/health",
  },
  ...resourceRegistry.map((resource) => ({
    id: resource.name,
    label: resource.label,
    description: resource.description,
    path: `/resources/${resource.name}`,
  })),
];