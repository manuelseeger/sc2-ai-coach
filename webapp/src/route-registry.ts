import type { AdminArea, ResourceDefinition } from "./types";

export const resourceRegistry: ResourceDefinition[] = [
  {
    name: "replays",
    label: "Replays",
    description: "Replay documents and replay-centric relationships.",
    writable: true,
  },
  {
    name: "metadata",
    label: "Metadata",
    description: "Operator-authored replay annotations.",
    writable: true,
  },
  {
    name: "players",
    label: "Players",
    description: "Known player identities, aliases, and portrait helpers.",
    writable: true,
  },
  {
    name: "sessions",
    label: "Sessions",
    description: "Read-only coaching session aggregates.",
    writable: false,
  },
  {
    name: "conversations",
    label: "Conversations",
    description: "Top-level persisted coaching exchanges.",
    writable: true,
  },
  {
    name: "conversation-items",
    label: "Conversation Items",
    description: "Read-only transcript records across conversations.",
    writable: false,
  },
  {
    name: "responses",
    label: "Responses",
    description: "Read-only response audit and accounting records.",
    writable: false,
  },
];

export const adminAreas: AdminArea[] = [
  {
    id: "workspace",
    label: "Workspace",
    description: "Start from the documented admin areas and fixed route families.",
    path: "/",
  },
  {
    id: "sessions-review",
    label: "Sessions",
    description: "Recent coaching sessions with a dedicated read-only inbox and detail flow.",
    path: "/sessions",
  },
  {
    id: "health",
    label: "Health",
    description: "Inspect backend readiness via the admin API.",
    path: "/health",
  },
  ...resourceRegistry.map((resource) => ({
    id: resource.name,
    label: resource.label,
    description: resource.description,
    path: `/resources/${resource.name}`,
  })),
];