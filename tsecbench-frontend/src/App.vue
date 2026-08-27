<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { settings, settingsReady } from './api/settings'

const route = useRoute()

const navItems = [
  { path: '/', label: '题目列表' },
  { path: '/settings', label: '设置' },
]

const ready = computed(() => settingsReady())
</script>

<template>
  <header class="topbar">
    <div class="container topbar-inner">
      <router-link to="/" class="brand mono">TSecBench 控制台</router-link>
      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: route.path === item.path }"
        >
          {{ item.label }}
        </router-link>
        <span v-if="!ready" class="warn-dot" title="未配置平台地址 / Token">未配置</span>
        <span v-else class="ok-dot" title="平台配置完成">就绪</span>
      </nav>
    </div>
  </header>
  <main class="container">
    <router-view />
  </main>
</template>

<style scoped>
.topbar {
  border-bottom: 1px solid var(--border);
  background: var(--bg-panel);
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  padding-bottom: 12px;
}

.brand {
  font-weight: 700;
  color: var(--text);
  font-size: 15px;
}

.nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-link {
  padding: 6px 12px;
  border-radius: 6px;
  color: var(--text-dim);
  font-size: 13px;
}

.nav-link:hover {
  color: var(--text);
  background: var(--bg-card);
}

.nav-link.active {
  color: var(--text);
  background: var(--bg-card);
  border: 1px solid var(--border);
}

.warn-dot {
  font-size: 12px;
  color: var(--yellow);
  border: 1px solid var(--yellow);
  border-radius: 999px;
  padding: 2px 10px;
}

.ok-dot {
  font-size: 12px;
  color: var(--green);
  border: 1px solid var(--green);
  border-radius: 999px;
  padding: 2px 10px;
}
</style>
