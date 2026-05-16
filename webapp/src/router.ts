import { createRouter, createWebHistory } from "vue-router";

import { resourceRegistry } from "./route-registry";
import HealthView from "./views/HealthView.vue";
import ResourcePlaceholderView from "./views/ResourcePlaceholderView.vue";
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

export const router = createRouter({
  history: createWebHistory(),
  routes,
});