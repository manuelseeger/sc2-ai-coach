import ConversationCreateView from "./views/ConversationCreateView.vue";
import ConversationDetailView from "./views/ConversationDetailView.vue";
import ConversationInboxView from "./views/ConversationInboxView.vue";
import ConversationResourceDetailView from "./views/ConversationResourceDetailView.vue";
import ConversationResourceInboxView from "./views/ConversationResourceInboxView.vue";
import { resourceRegistry } from "./route-registry";
import MetadataCreateView from "./views/MetadataCreateView.vue";
import MetadataDetailView from "./views/MetadataDetailView.vue";
import MetadataInboxView from "./views/MetadataInboxView.vue";
import PlayerCreateView from "./views/PlayerCreateView.vue";
import PlayerDetailView from "./views/PlayerDetailView.vue";
import PlayerInboxView from "./views/PlayerInboxView.vue";
import PlayerResourceDetailView from "./views/PlayerResourceDetailView.vue";
import PlayerResourceInboxView from "./views/PlayerResourceInboxView.vue";
import HealthView from "./views/HealthView.vue";
import ReplayCreateView from "./views/ReplayCreateView.vue";
import ReplayDetailView from "./views/ReplayDetailView.vue";
import ReplayInboxView from "./views/ReplayInboxView.vue";
import ReplayResourceDetailView from "./views/ReplayResourceDetailView.vue";
import ReplayResourceInboxView from "./views/ReplayResourceInboxView.vue";
import ResourcePlaceholderView from "./views/ResourcePlaceholderView.vue";
import SessionDetailView from "./views/SessionDetailView.vue";
import SessionInboxView from "./views/SessionInboxView.vue";
import WorkspaceView from "./views/WorkspaceView.vue";

const placeholderResources = resourceRegistry.filter(
  (resource) => !["conversations", "metadata", "players", "replays"].includes(resource.name),
);

export const routes = [
  {
    path: "/",
    name: "workspace",
    component: WorkspaceView,
  },
  {
    path: "/health",
    name: "health",
    component: HealthView,
  },
  {
    path: "/sessions",
    name: "sessions-inbox",
    component: SessionInboxView,
  },
  {
    path: "/sessions/:sessionId",
    name: "session-detail",
    component: SessionDetailView,
    props: true,
  },
  {
    path: "/conversations",
    name: "conversations-inbox",
    component: ConversationInboxView,
  },
  {
    path: "/conversations/:conversationId",
    name: "conversation-detail",
    component: ConversationDetailView,
    props: true,
  },
  {
    path: "/replays",
    name: "replays-inbox",
    component: ReplayInboxView,
  },
  {
    path: "/replays/:replayId",
    name: "replay-detail",
    component: ReplayDetailView,
    props: true,
  },
  {
    path: "/players",
    name: "players-inbox",
    component: PlayerInboxView,
  },
  {
    path: "/players/:toonHandle",
    name: "player-detail",
    component: PlayerDetailView,
    props: true,
  },
  {
    path: "/resources/replays",
    name: "replay-resource-inbox",
    component: ReplayResourceInboxView,
  },
  {
    path: "/resources/replays/new",
    name: "replay-resource-create",
    component: ReplayCreateView,
  },
  {
    path: "/resources/replays/:replayId",
    name: "replay-resource-detail",
    component: ReplayResourceDetailView,
    props: true,
  },
  {
    path: "/resources/conversations",
    name: "conversation-resource-inbox",
    component: ConversationResourceInboxView,
  },
  {
    path: "/resources/conversations/new",
    name: "conversation-resource-create",
    component: ConversationCreateView,
  },
  {
    path: "/resources/conversations/:conversationId",
    name: "conversation-resource-detail",
    component: ConversationResourceDetailView,
    props: true,
  },
  {
    path: "/resources/metadata",
    name: "metadata-inbox",
    component: MetadataInboxView,
  },
  {
    path: "/resources/metadata/new",
    name: "metadata-create",
    component: MetadataCreateView,
  },
  {
    path: "/resources/metadata/:metadataId",
    name: "metadata-detail",
    component: MetadataDetailView,
    props: true,
  },
  {
    path: "/resources/players",
    name: "player-resource-inbox",
    component: PlayerResourceInboxView,
  },
  {
    path: "/resources/players/new",
    name: "player-resource-create",
    component: PlayerCreateView,
  },
  {
    path: "/resources/players/:toonHandle",
    name: "player-resource-detail",
    component: PlayerResourceDetailView,
    props: true,
  },
  ...placeholderResources.map((resource) => ({
    path: `/resources/${resource.name}`,
    name: resource.name,
    component: ResourcePlaceholderView,
    props: {
      resource,
    },
  })),
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];