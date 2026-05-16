import { resourceRegistry } from "./route-registry";
import MetadataCreateView from "./views/MetadataCreateView.vue";
import MetadataDetailView from "./views/MetadataDetailView.vue";
import MetadataInboxView from "./views/MetadataInboxView.vue";
import HealthView from "./views/HealthView.vue";
import ResourcePlaceholderView from "./views/ResourcePlaceholderView.vue";
import SessionDetailView from "./views/SessionDetailView.vue";
import SessionInboxView from "./views/SessionInboxView.vue";
import WorkspaceView from "./views/WorkspaceView.vue";

const placeholderResources = resourceRegistry.filter((resource) => resource.name !== "metadata");

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