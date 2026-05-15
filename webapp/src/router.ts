import { createRouter, createWebHistory } from 'vue-router'

import ConversationDetailView from './views/ConversationDetailView.vue'
import ConversationsView from './views/ConversationsView.vue'
import GenericResourceDetailView from './views/GenericResourceDetailView.vue'
import GenericResourceListView from './views/GenericResourceListView.vue'
import MapStatsView from './views/MapStatsView.vue'
import PlayerDetailView from './views/PlayerDetailView.vue'
import PlayersView from './views/PlayersView.vue'
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
    { path: '/players', component: PlayersView },
    { path: '/players/:toonHandle', component: PlayerDetailView },
    { path: '/resources/:resourceName', component: GenericResourceListView },
    { path: '/resources/:resourceName/new', component: GenericResourceDetailView },
    { path: '/resources/:resourceName/:documentId', component: GenericResourceDetailView },
    { path: '/replays/:replayId', component: ReplayDetailView },
    { path: '/map-stats', component: MapStatsView },
  ],
})