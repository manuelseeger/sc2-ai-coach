import { createRouter, createWebHistory } from 'vue-router'

import ConversationDetailView from './views/ConversationDetailView.vue'
import ConversationsView from './views/ConversationsView.vue'
import MapStatsView from './views/MapStatsView.vue'
import ReplayDetailView from './views/ReplayDetailView.vue'
import SessionDetailView from './views/SessionDetailView.vue'
import SessionsView from './views/SessionsView.vue'
import WorkspaceView from './views/WorkspaceView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: WorkspaceView },
    { path: '/sessions', component: SessionsView },
    { path: '/sessions/:sessionId', component: SessionDetailView },
    { path: '/conversations', component: ConversationsView },
    { path: '/conversations/:conversationId', component: ConversationDetailView },
    { path: '/replays/:replayId', component: ReplayDetailView },
    { path: '/map-stats', component: MapStatsView },
  ],
})