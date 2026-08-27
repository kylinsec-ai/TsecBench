import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import ChallengesView from './views/ChallengesView.vue'
import ChallengeRunView from './views/ChallengeRunView.vue'
import SettingsView from './views/SettingsView.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ChallengesView },
    { path: '/challenges/:uniqueCode', component: ChallengeRunView, props: true },
    { path: '/settings', component: SettingsView },
  ],
})

createApp(App).use(router).mount('#app')
