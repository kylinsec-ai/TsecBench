<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { settingsReady } from './api/settings'

const route = useRoute()

const navItems = [
  { path: '/', label: 'Dashboard', caption: '总览', index: '01' },
  { path: '/settings', label: 'Settings', caption: '连接与 AI', index: '02' },
]

const ready = computed(() => settingsReady())
const isChallengeRoute = computed(() => route.path.startsWith('/challenges/'))

const currentPage = computed(() => {
  if (isChallengeRoute.value) return { kicker: 'RUN / WORKSPACE', title: '题目工作区' }
  if (route.path === '/settings') return { kicker: 'SYSTEM / CONFIG', title: 'Settings' }
  return { kicker: 'OVERVIEW / DASHBOARD', title: 'Dashboard' }
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <router-link to="/" class="brand-lockup" aria-label="返回 Dashboard">
        <span class="brand-mark">TSB</span>
        <span class="brand-name">FIELD<br />CONSOLE</span>
        <span class="brand-version mono">v1 / BENCH</span>
      </router-link>

      <div class="sidebar-rule"></div>
      <p class="nav-label">WORKSPACE</p>
      <nav class="side-nav" aria-label="主导航">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="side-nav-link"
          :class="{
            active: item.path === '/' ? route.path === '/' || isChallengeRoute : route.path === item.path,
          }"
          :aria-current="item.path === '/' ? (route.path === '/' || isChallengeRoute ? 'page' : undefined) : route.path === item.path ? 'page' : undefined"
        >
          <span class="nav-index mono">{{ item.index }}</span>
          <span class="nav-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.caption }}</small>
          </span>
          <span class="nav-arrow" aria-hidden="true">↗</span>
        </router-link>
      </nav>

      <div class="sidebar-spacer"></div>
      <div class="connection-card" :class="{ ready }">
        <span class="connection-indicator" aria-hidden="true"></span>
        <div>
          <span class="connection-label mono">PLATFORM LINK</span>
          <strong>{{ ready ? '连接已就绪' : '需要配置' }}</strong>
        </div>
      </div>
      <router-link v-if="!ready" to="/settings" class="setup-link">配置连接 →</router-link>
      <p class="sidebar-meta mono">LOCAL SESSION<br />tokens stay in browser</p>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="mobile-brand">
          <span class="brand-mark brand-mark-small">TSB</span>
          <span class="brand-name">FIELD CONSOLE</span>
        </div>
        <div class="breadcrumb">
          <span class="topbar-kicker mono">{{ currentPage.kicker }}</span>
          <span class="topbar-page">{{ currentPage.title }}</span>
        </div>
        <div class="topbar-right">
          <span class="sync-state" :class="{ ready }">
            <i aria-hidden="true"></i>{{ ready ? 'Platform ready' : 'Setup required' }}
          </span>
          <router-link to="/settings" class="topbar-settings" aria-label="打开设置">◎</router-link>
        </div>
      </header>

      <main class="page-container">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 28px 18px 22px;
  background: rgba(18, 21, 37, 0.94);
  border-right: 1px solid var(--border);
}

.brand-lockup {
  position: relative;
  display: grid;
  grid-template-columns: 40px 1fr;
  align-items: center;
  column-gap: 11px;
  min-height: 44px;
  color: var(--text);
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid var(--accent);
  color: var(--accent);
  font: 700 12px/1 var(--mono);
  letter-spacing: -0.08em;
}

.brand-mark-small {
  width: 30px;
  height: 30px;
  font-size: 10px;
}

.brand-name {
  font: 700 12px/1.15 var(--display);
  letter-spacing: 0.08em;
}

.brand-version {
  position: absolute;
  top: 49px;
  left: 51px;
  color: var(--text-dim);
  font-size: 9px;
  letter-spacing: 0.08em;
}

.sidebar-rule {
  height: 1px;
  margin: 48px 8px 22px;
  background: var(--border);
}

.nav-label,
.connection-label {
  margin: 0 8px 10px;
  color: var(--text-dim);
  font-size: 9px;
  letter-spacing: 0.14em;
}

.side-nav {
  display: grid;
  gap: 5px;
}

.side-nav-link {
  display: grid;
  grid-template-columns: 28px 1fr 20px;
  align-items: center;
  min-height: 54px;
  padding: 7px 9px;
  border: 1px solid transparent;
  color: var(--text-dim);
  transition: border-color 180ms ease, background 180ms ease, color 180ms ease;
}

.side-nav-link:hover,
.side-nav-link.active {
  color: var(--text);
  border-color: var(--border-strong);
  background: linear-gradient(90deg, rgba(145, 226, 208, 0.08), rgba(145, 226, 208, 0));
}

.side-nav-link.active {
  border-left-color: var(--accent);
}

.nav-index {
  color: var(--text-dim);
  font-size: 10px;
}

.side-nav-link.active .nav-index,
.side-nav-link.active .nav-arrow {
  color: var(--accent);
}

.nav-copy {
  display: grid;
  gap: 3px;
}

.nav-copy strong {
  font: 600 13px/1.1 var(--display);
  letter-spacing: 0.01em;
}

.nav-copy small {
  color: var(--text-dim);
  font-size: 10px;
}

.nav-arrow {
  color: var(--border-strong);
  font-size: 15px;
  text-align: right;
}

.sidebar-spacer {
  flex: 1;
}

.connection-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 4px 10px;
  padding: 11px 10px;
  border: 1px solid var(--border);
  background: rgba(14, 17, 32, 0.62);
}

.connection-card.ready {
  border-color: rgba(145, 226, 208, 0.38);
}

.connection-indicator,
.sync-state i {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  display: block;
  border-radius: 50%;
  background: var(--risk);
  box-shadow: 0 0 0 3px rgba(255, 149, 126, 0.1);
}

.connection-card.ready .connection-indicator,
.sync-state.ready i {
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(145, 226, 208, 0.1);
}

.connection-card strong {
  display: block;
  color: var(--text);
  font-size: 11px;
  font-weight: 500;
}

.connection-label {
  display: block;
  margin: 0 0 5px;
  font-size: 8px;
}

.setup-link {
  margin: 0 8px 24px;
  color: var(--accent);
  font: 11px/1.4 var(--mono);
}

.sidebar-meta {
  margin: 0 8px;
  color: var(--text-dim);
  font-size: 8px;
  line-height: 1.7;
  letter-spacing: 0.08em;
}

.main-shell {
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 40px;
  border-bottom: 1px solid rgba(52, 58, 86, 0.72);
  background: rgba(14, 17, 32, 0.88);
  backdrop-filter: blur(18px);
}

.breadcrumb {
  display: grid;
  gap: 5px;
}

.topbar-kicker {
  color: var(--text-dim);
  font-size: 9px;
  letter-spacing: 0.13em;
}

.topbar-page {
  color: var(--text);
  font: 600 14px/1 var(--display);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.sync-state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--risk);
  font: 10px/1 var(--mono);
}

.sync-state.ready {
  color: var(--accent);
}

.topbar-settings {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 17px;
  transition: border-color 180ms ease, color 180ms ease;
}

.topbar-settings:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.mobile-brand {
  display: none;
  align-items: center;
  gap: 9px;
}

.page-container {
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 38px 40px 72px;
}

@media (max-width: 820px) {
  .app-shell {
    display: block;
  }

  .sidebar {
    position: static;
    height: auto;
    display: block;
    padding: 14px 16px 12px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .brand-lockup,
  .sidebar-rule,
  .sidebar-spacer,
  .connection-card,
  .setup-link,
  .sidebar-meta {
    display: none;
  }

  .nav-label {
    display: none;
  }

  .side-nav {
    display: flex;
    gap: 6px;
  }

  .side-nav-link {
    flex: 1;
    grid-template-columns: 24px 1fr;
    min-height: 44px;
    padding: 6px 8px;
  }

  .nav-copy small,
  .nav-arrow {
    display: none;
  }

  .topbar {
    position: static;
    min-height: 62px;
    padding: 12px 16px;
  }

  .mobile-brand {
    display: flex;
  }

  .breadcrumb {
    display: none;
  }

  .topbar-right {
    margin-left: auto;
  }

  .sync-state {
    font-size: 9px;
  }

  .page-container {
    padding: 28px 16px 48px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .side-nav-link,
  .topbar-settings {
    transition: none;
  }
}
</style>
