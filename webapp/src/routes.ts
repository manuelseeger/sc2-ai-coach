import { resourceRegistry } from "./route-registry";
import HealthView from "./views/HealthView.vue";
import ResourcePlaceholderView from "./views/ResourcePlaceholderView.vue";
import SessionDetailView from "./views/SessionDetailView.vue";
import SessionInboxView from "./views/SessionInboxView.vue";
import WorkspaceView from "./views/WorkspaceView.vue";

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
  ...resourceRegistry.map((resource) => ({
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