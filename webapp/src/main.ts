import { createApp } from 'vue'

import App from './App.vue'
import { adminApiKey, createAdminApiClient } from './api'
import { router } from './router'
import './style.css'

const app = createApp(App)
app.provide(adminApiKey, createAdminApiClient())
app.use(router)
app.mount('#app')