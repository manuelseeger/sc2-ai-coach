import { createRouter, createWebHistory } from 'vue-router'

import ConversationDetailView from './views/ConversationDetailView.vue'
import ConversationsView from './views/ConversationsView.vue'
import MapStatsView from './views/MapStatsView.vue'
import WorkspaceView from './views/WorkspaceView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: WorkspaceView },
    { path: '/conversations', component: ConversationsView },
    { path: '/conversations/:conversationId', component: ConversationDetailView },
    { path: '/map-stats', component: MapStatsView },
  ],
})