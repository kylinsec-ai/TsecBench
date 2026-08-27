<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/tsecbench'
import { llmReady, settingsReady } from '../api/settings'
import { createSolveSession } from '../composables/useSolver'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const error = ref('')
const autoRunning = ref(false)
const showLog = ref(false)
const autoLogs = ref([])
const activeFilter = ref('all')
const maxActive = 3

const filterTabs = [
  { key: 'all', label: '全部' },
  { key: 'actionable', label: '可行动' },
  { key: 'active', label: '运行中' },
  { key: 'done', label: '已通关' },
]

const platformReady = computed(() => settingsReady())
const aiConfigured = computed(() => llmReady())

const stats = computed(() => {
  const activeCount = list.value.filter((challenge) =>
    ['pending', 'available', 'stop_pending'].includes(challenge.container_status)
  ).length
  const completed = list.value.filter((challenge) => challenge.is_completed).length
  return {
    total: list.value.length,
    actionable: list.value.filter((challenge) => !challenge.is_completed).length,
    active: activeCount,
    completed,
    slots: Math.max(0, maxActive - activeCount),
  }
})

const filterCounts = computed(() => ({
  all: list.value.length,
  actionable: list.value.filter((challenge) => !challenge.is_completed).length,
  active: list.value.filter((challenge) =>
    ['pending', 'available', 'stop_pending'].includes(challenge.container_status)
  ).length,
  done: list.value.filter((challenge) => challenge.is_completed).length,
}))

const visibleList = computed(() => {
  if (activeFilter.value === 'actionable') return list.value.filter((challenge) => !challenge.is_completed)
  if (activeFilter.value === 'active') {
    return list.value.filter((challenge) =>
      ['pending', 'available', 'stop_pending'].includes(challenge.container_status)
    )
  }
  if (activeFilter.value === 'done') return list.value.filter((challenge) => challenge.is_completed)
  return list.value
})

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    list.value = await api.listChallenges()
  } catch (err) {
    error.value = `加载失败 [${err.code || err.status}]: ${err.message}`
  } finally {
    loading.value = false
  }
}

onMounted(load)

function difficultyClass(difficulty) {
  return String(difficulty || '').toLowerCase()
}

function difficultyLabel(difficulty) {
  const labels = { easy: 'EASY', medium: 'MEDIUM', hard: 'HARD' }
  return labels[difficultyClass(difficulty)] || String(difficulty || 'UNKNOWN').toUpperCase()
}

function statusLabel(status) {
  const labels = {
    available: '已就绪',
    pending: '启动中',
    stop_pending: '停止中',
    stopped: '已停止',
  }
  return labels[status] || '未知状态'
}

function statusTone(status) {
  if (status === 'available') return 'ready'
  if (status === 'pending' || status === 'stop_pending') return 'warming'
  return 'quiet'
}

function progressPercent(challenge) {
  return Math.min(
    100,
    Math.round((challenge.correct_flag_count / Math.max(1, challenge.flag_count)) * 100)
  )
}

function openChallenge(code) {
  router.push({ path: `/challenges/${encodeURIComponent(code)}` })
}

function selectFilter(filter) {
  activeFilter.value = filter
}

async function autoRunOne(challenge) {
  const session = createSolveSession(challenge)
  await session.autoSolve()
  session.session.logs.forEach((log) =>
    autoLogs.value.push({ time: log.time, type: log.type, text: `[${session.uniqueCode}] ${log.text}` })
  )
  await load()
}

async function autoRunAll() {
  if (autoRunning.value) return
  if (!settingsReady()) {
    autoLogs.value.push({ time: now(), type: 'error', text: '请先在「Settings」中配置平台地址与 Token' })
    showLog.value = true
    return
  }
  autoRunning.value = true
  showLog.value = true
  autoLogs.value = []
  try {
    const targets = list.value.filter((challenge) => !challenge.is_completed)
    if (!targets.length) {
      autoLogs.value.push({ time: now(), type: 'info', text: '没有未完成的题目' })
      return
    }
    autoLogs.value.push({ time: now(), type: 'info', text: `开始顺序自动解 ${targets.length} 道题` })
    for (const challenge of targets) {
      autoLogs.value.push({
        time: now(),
        type: 'warn',
        text: `===== 开始自动解 ${challenge.unique_code} =====`,
      })
      await autoRunOne(challenge)
    }
    autoLogs.value.push({ time: now(), type: 'success', text: '全部自动解题结束' })
  } finally {
    autoRunning.value = false
  }
}
</script>

<template>
  <div class="dashboard">
    <section class="dashboard-hero">
      <div class="hero-copy">
        <p class="eyebrow mono">FIELD REPORT / {{ stats.total || '—' }} CHALLENGES</p>
        <h1>今天要攻哪一面？</h1>
        <p class="hero-subtitle">从可访问目标开始。这里显示当前任务的资源、进度与 AI 队列，下一步永远只留一个安全入口。</p>
      </div>
      <div class="hero-actions">
        <button class="quiet-button" :disabled="loading" @click="load">
          <span class="button-glyph" aria-hidden="true">↻</span>{{ loading ? '同步中' : '刷新任务' }}
        </button>
        <button class="ai" :disabled="autoRunning" @click="autoRunAll">
          <span class="button-glyph" aria-hidden="true">✦</span>{{ autoRunning ? '自动解题中' : '全部自动解' }}
        </button>
      </div>
    </section>

    <div class="dashboard-rule" aria-hidden="true"></div>

    <section class="metric-strip" aria-label="任务概览">
      <article class="metric-card metric-emphasis">
        <span class="metric-label"><i></i>可行动题目</span>
        <strong>{{ stats.actionable }}</strong>
        <span class="metric-note">等待你的下一步</span>
      </article>
      <article class="metric-card">
        <span class="metric-label"><i class="dot-violet"></i>运行中实例</span>
        <strong>{{ stats.active }}</strong>
        <span class="metric-note">容器生命周期活动</span>
      </article>
      <article class="metric-card">
        <span class="metric-label"><i class="dot-muted"></i>已通关</span>
        <strong>{{ stats.completed }}</strong>
        <span class="metric-note">共 {{ stats.total }} 道题</span>
      </article>
      <article class="metric-card">
        <span class="metric-label"><i class="dot-coral"></i>剩余资源位</span>
        <strong>{{ stats.slots }}</strong>
        <span class="metric-note">上限 {{ maxActive }} 个实例</span>
      </article>
    </section>

    <div v-if="error" class="notice notice-error" role="alert">
      <div><span class="notice-kicker mono">PLATFORM RESPONSE</span><strong>{{ error }}</strong></div>
      <router-link to="/settings" class="notice-link">去 Settings →</router-link>
    </div>

    <div class="dashboard-layout">
      <section class="challenge-section">
        <div class="section-header">
          <div>
            <p class="eyebrow mono">CHALLENGE FIELD</p>
            <h2>题目</h2>
          </div>
          <div class="filter-tabs" role="tablist" aria-label="筛选题目">
            <button
              v-for="tab in filterTabs"
              :key="tab.key"
              class="filter-tab"
              :class="{ active: activeFilter === tab.key }"
              role="tab"
              :aria-selected="activeFilter === tab.key"
              @click="selectFilter(tab.key)"
            >
              {{ tab.label }} <span>{{ filterCounts[tab.key] }}</span>
            </button>
          </div>
        </div>

        <div v-if="loading && !list.length" class="challenge-grid" aria-label="加载题目">
          <div v-for="i in 4" :key="i" class="challenge-skeleton"></div>
        </div>

        <div v-else-if="visibleList.length" class="challenge-grid">
          <button
            v-for="challenge in visibleList"
            :key="challenge.unique_code"
            type="button"
            class="challenge-card"
            :class="{
              'is-done': challenge.is_completed,
              'is-live': challenge.container_status === 'available',
            }"
            :aria-label="`打开题目 ${challenge.unique_code}`"
            @click="openChallenge(challenge.unique_code)"
          >
            <span class="card-spine" :class="statusTone(challenge.container_status)" aria-hidden="true"></span>
            <span class="challenge-card-top">
              <span class="challenge-code mono">{{ challenge.unique_code }}</span>
              <span class="challenge-status" :class="statusTone(challenge.container_status)">
                <i aria-hidden="true"></i>{{ statusLabel(challenge.container_status) }}
              </span>
            </span>
            <span class="challenge-description">{{ challenge.description || '暂无描述，进入题目查看可用上下文。' }}</span>
            <span class="challenge-meta mono">
              <span>{{ difficultyLabel(challenge.difficulty) }}</span>
              <span>LV.{{ challenge.level }}</span>
              <span>{{ challenge.total_score }} PTS</span>
            </span>
            <span
              class="flag-track"
              role="progressbar"
              :aria-valuenow="challenge.correct_flag_count"
              :aria-valuemin="0"
              :aria-valuemax="challenge.flag_count"
              :aria-label="`${challenge.correct_flag_count} / ${challenge.flag_count} flags`"
            >
              <i
                v-for="flagIndex in Math.max(1, challenge.flag_count)"
                :key="flagIndex"
                :class="{ complete: flagIndex <= challenge.correct_flag_count }"
              ></i>
            </span>
            <span class="challenge-card-bottom mono">
              <span>{{ challenge.correct_flag_count }}/{{ challenge.flag_count }} FLAGS</span>
              <span v-if="challenge.is_completed" class="bottom-done">CLEARED</span>
              <span v-else-if="challenge.container_addr && challenge.container_addr.length" class="bottom-target">TARGET LIVE</span>
              <span v-else>ENTER →</span>
            </span>
          </button>
        </div>

        <div v-else-if="!loading" class="empty-state">
          <span class="empty-mark mono">∅</span>
          <div>
            <strong>{{ activeFilter === 'all' ? '暂无题目' : '此筛选暂无题目' }}</strong>
            <p>{{ activeFilter === 'all' ? '请确认 Token 与平台地址，或在后端 seed 任务。' : '切换筛选，查看其他任务状态。' }}</p>
          </div>
          <router-link v-if="activeFilter === 'all'" to="/settings">检查连接 →</router-link>
        </div>
      </section>

      <aside class="automation-panel">
        <div class="automation-head">
          <div>
            <p class="eyebrow mono">AUTOMATION / AI</p>
            <h2>自动化队列</h2>
          </div>
          <span class="ai-state" :class="{ ready: aiConfigured }">{{ aiConfigured ? 'READY' : 'SETUP' }}</span>
        </div>

        <div class="automation-status" :class="{ running: autoRunning }">
          <span class="automation-pulse" aria-hidden="true"></span>
          <div>
            <strong>{{ autoRunning ? '队列正在运行' : '队列待命' }}</strong>
            <span>{{ autoRunning ? '按顺序处理未通关题目' : '选择全部自动解开始运行' }}</span>
          </div>
        </div>

        <div class="queue-list">
          <div class="queue-row">
            <span class="queue-label mono">PLATFORM</span>
            <span :class="platformReady ? 'queue-good' : 'queue-risk'">{{ platformReady ? '连接已就绪' : '需要配置' }}</span>
          </div>
          <div class="queue-row">
            <span class="queue-label mono">MODEL</span>
            <span :class="aiConfigured ? 'queue-good' : 'queue-risk'">{{ aiConfigured ? 'LLM 已配置' : '等待 API Key' }}</span>
          </div>
          <div class="queue-row">
            <span class="queue-label mono">HINT COST</span>
            <span class="queue-neutral">默认关闭</span>
          </div>
          <div class="queue-row">
            <span class="queue-label mono">RESOURCE</span>
            <span class="queue-neutral">{{ stats.active }} / {{ maxActive }} 实例</span>
          </div>
        </div>

        <div class="automation-callout">
          <span class="callout-mark" aria-hidden="true">!</span>
          <p>AI 会按顺序提交候选 flag。提示默认关闭，避免无意中触发扣分。</p>
        </div>
        <router-link to="/settings" class="automation-link">调整自动化设置 →</router-link>
      </aside>
    </div>

    <section v-if="showLog" class="automation-log">
      <div class="log-head">
        <div><p class="eyebrow mono">LIVE OUTPUT</p><h2>自动解题日志</h2></div>
        <button class="quiet-button small" @click="showLog = false">收起</button>
      </div>
      <div class="log-body mono" aria-live="polite">
        <div v-for="(log, index) in autoLogs" :key="index" class="log-line" :class="`log-${log.type}`">
          <span class="log-time">{{ log.time }}</span>{{ log.text }}
        </div>
        <div v-if="!autoLogs.length" class="dim">暂无日志</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  animation: page-in 420ms ease both;
}

.dashboard-hero,
.section-header,
.automation-head,
.log-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.hero-copy {
  max-width: 680px;
}

.eyebrow {
  margin: 0;
  color: var(--text-dim);
  font-size: 9px;
  letter-spacing: 0.15em;
  line-height: 1.3;
}

.dashboard h1 {
  margin: 10px 0 8px;
  color: var(--text);
  font: 600 clamp(32px, 4vw, 58px)/0.98 var(--display);
  letter-spacing: -0.06em;
}

.hero-subtitle {
  max-width: 560px;
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.quiet-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 36, 56, 0.58);
}

.button-glyph {
  color: var(--accent);
  font-size: 15px;
}

.dashboard-rule {
  height: 1px;
  margin: 28px 0 16px;
  background: linear-gradient(90deg, var(--border-strong), rgba(82, 93, 134, 0.05));
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 28px;
}

.metric-card {
  min-height: 116px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 14px 15px;
  background: rgba(23, 26, 42, 0.78);
  border: 1px solid var(--border);
}

.metric-emphasis {
  border-top-color: var(--accent);
}

.metric-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-dim);
  font-size: 11px;
}

.metric-label i {
  width: 6px;
  height: 6px;
  display: block;
  border-radius: 50%;
  background: var(--accent);
}

.metric-label .dot-violet,
.dot-violet {
  background: var(--ai);
}

.metric-label .dot-muted,
.dot-muted {
  background: var(--text-dim);
}

.metric-label .dot-coral,
.dot-coral {
  background: var(--risk);
}

.metric-card strong {
  color: var(--text);
  font: 500 36px/1 var(--display);
  letter-spacing: -0.06em;
}

.metric-note {
  color: var(--text-dim);
  font: 9px/1 var(--mono);
}

.notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 26px;
  padding: 13px 15px;
  border: 1px solid rgba(255, 149, 126, 0.55);
  background: rgba(255, 149, 126, 0.05);
}

.notice > div {
  display: grid;
  gap: 4px;
}

.notice-kicker {
  color: var(--risk);
  font-size: 8px;
  letter-spacing: 0.12em;
}

.notice strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
}

.notice-link {
  flex: 0 0 auto;
  color: var(--risk);
  font: 11px/1 var(--mono);
}

.dashboard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 274px;
  align-items: start;
  gap: 22px;
}

.section-header {
  align-items: end;
  margin-bottom: 13px;
}

.dashboard h2 {
  margin: 5px 0 0;
  color: var(--text);
  font: 600 22px/1 var(--display);
  letter-spacing: -0.04em;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  padding: 3px;
  background: rgba(23, 26, 42, 0.72);
  border: 1px solid var(--border);
}

.filter-tab {
  padding: 6px 8px;
  color: var(--text-dim);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  font: 10px/1 var(--mono);
}

.filter-tab:hover:not(:disabled) {
  color: var(--text);
  background: rgba(82, 93, 134, 0.18);
  border-color: transparent;
  transform: none;
}

.filter-tab.active {
  color: var(--accent-ink);
  background: var(--accent);
  border-color: var(--accent);
}

.filter-tab span {
  margin-left: 3px;
  opacity: 0.7;
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.challenge-card {
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 11px;
  padding: 15px 15px 14px 18px;
  overflow: hidden;
  color: var(--text);
  text-align: left;
  background: rgba(23, 26, 42, 0.88);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease, box-shadow 180ms ease;
}

.challenge-card:hover {
  background: rgba(30, 36, 56, 0.95);
  border-color: var(--border-strong);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
  transform: translateY(-2px);
}

.challenge-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.challenge-card.is-done {
  opacity: 0.68;
}

.challenge-card.is-done:hover {
  opacity: 0.9;
}

.card-spine {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  background: var(--text-dim);
}

.card-spine.ready {
  background: var(--accent);
}

.card-spine.warming {
  background: var(--warning);
}

.challenge-card-top,
.challenge-card-bottom,
.challenge-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.challenge-code {
  min-width: 0;
  overflow: hidden;
  color: var(--text);
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.challenge-status {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 5px;
  color: var(--text-dim);
  font: 9px/1 var(--mono);
  white-space: nowrap;
}

.challenge-status i {
  width: 5px;
  height: 5px;
  display: block;
  border-radius: 50%;
  background: var(--text-dim);
}

.challenge-status.ready {
  color: var(--accent);
}

.challenge-status.ready i {
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(145, 226, 208, 0.1);
}

.challenge-status.warming {
  color: var(--warning);
}

.challenge-status.warming i {
  background: var(--warning);
}

.challenge-description {
  display: -webkit-box;
  overflow: hidden;
  min-height: 42px;
  color: var(--text-dim);
  font-size: 12px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.challenge-meta {
  justify-content: flex-start;
  color: var(--text-dim);
  font-size: 9px;
}

.flag-track {
  display: flex;
  gap: 4px;
  width: 100%;
}

.flag-track i {
  height: 4px;
  flex: 1;
  min-width: 6px;
  background: #343a56;
}

.flag-track i.complete {
  background: var(--accent);
}

.challenge-card-bottom {
  color: var(--text-dim);
  font-size: 9px;
}

.bottom-done,
.bottom-target {
  color: var(--accent);
}

.challenge-skeleton {
  min-height: 182px;
  background: linear-gradient(110deg, rgba(23, 26, 42, 0.8) 35%, rgba(52, 58, 86, 0.45) 50%, rgba(23, 26, 42, 0.8) 65%);
  background-size: 200% 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  animation: skeleton 1.5s linear infinite;
}

.empty-state {
  min-height: 184px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 22px;
  background: rgba(23, 26, 42, 0.62);
  border: 1px dashed var(--border-strong);
}

.empty-mark {
  color: var(--accent);
  font-size: 24px;
}

.empty-state strong {
  display: block;
  color: var(--text);
  font-size: 13px;
}

.empty-state p {
  margin: 4px 0 0;
  color: var(--text-dim);
  font-size: 12px;
}

.empty-state a {
  margin-left: auto;
  font: 10px/1 var(--mono);
}

.automation-panel {
  padding: 17px;
  background: rgba(23, 26, 42, 0.78);
  border: 1px solid var(--border);
}

.automation-head {
  align-items: flex-start;
  margin-bottom: 18px;
}

.ai-state {
  padding: 5px 6px;
  color: var(--text-dim);
  border: 1px solid var(--border);
  font: 9px/1 var(--mono);
}

.ai-state.ready {
  color: var(--ai);
  border-color: rgba(139, 124, 255, 0.65);
}

.automation-status {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background: rgba(14, 17, 32, 0.72);
  border: 1px solid var(--border);
}

.automation-status.running {
  border-color: rgba(139, 124, 255, 0.62);
}

.automation-pulse {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  margin-top: 3px;
  border-radius: 50%;
  background: var(--text-dim);
}

.automation-status.running .automation-pulse {
  background: var(--ai);
  box-shadow: 0 0 0 4px rgba(139, 124, 255, 0.12);
  animation: pulse 1.8s ease-in-out infinite;
}

.automation-status strong,
.automation-status span {
  display: block;
}

.automation-status strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
}

.automation-status span {
  margin-top: 4px;
  color: var(--text-dim);
  font-size: 10px;
}

.queue-list {
  margin-top: 18px;
  border-top: 1px solid var(--border);
}

.queue-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(52, 58, 86, 0.7);
  font-size: 10px;
}

.queue-label {
  color: var(--text-dim);
  font-size: 8px;
}

.queue-good {
  color: var(--accent);
}

.queue-risk {
  color: var(--risk);
}

.queue-neutral {
  color: var(--text);
}

.automation-callout {
  display: flex;
  gap: 9px;
  margin-top: 16px;
  padding: 10px;
  background: rgba(255, 149, 126, 0.05);
  border: 1px solid rgba(255, 149, 126, 0.3);
}

.callout-mark {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--risk);
  border: 1px solid var(--risk);
  border-radius: 50%;
  font: 10px/1 var(--mono);
}

.automation-callout p {
  margin: 0;
  color: var(--text-dim);
  font-size: 10px;
  line-height: 1.55;
}

.automation-link {
  display: block;
  margin-top: 16px;
  color: var(--ai);
  font: 10px/1 var(--mono);
}

.automation-log {
  margin-top: 22px;
  background: rgba(10, 12, 22, 0.84);
  border: 1px solid var(--border);
}

.log-head {
  align-items: center;
  padding: 13px 16px;
  border-bottom: 1px solid var(--border);
}

.log-head h2 {
  margin-top: 4px;
  font-size: 16px;
}

.log-body {
  max-height: 280px;
  overflow-y: auto;
  padding: 13px 16px;
  color: var(--text-dim);
  font-size: 11px;
  line-height: 1.8;
}

.log-line {
  word-break: break-word;
}

.log-time {
  display: inline-block;
  min-width: 66px;
  color: #65708f;
}

.log-success {
  color: var(--accent);
}

.log-error {
  color: var(--risk);
}

.log-warn {
  color: var(--warning);
}

.log-info,
.log-api {
  color: var(--text);
}

.dim {
  color: var(--text-dim);
}

@keyframes page-in {
  from { opacity: 0; transform: translateY(7px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes skeleton {
  to { background-position: -200% 0; }
}

@keyframes pulse {
  50% { opacity: 0.45; transform: scale(0.8); }
}

@media (max-width: 1080px) {
  .dashboard-layout {
    grid-template-columns: minmax(0, 1fr) 240px;
  }

  .metric-card strong {
    font-size: 31px;
  }
}

@media (max-width: 820px) {
  .dashboard-hero {
    display: block;
  }

  .hero-actions {
    margin-top: 18px;
  }

  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-layout {
    display: block;
  }

  .automation-panel {
    margin-top: 22px;
  }
}

@media (max-width: 560px) {
  .dashboard h1 {
    font-size: 37px;
  }

  .section-header {
    display: block;
  }

  .filter-tabs {
    margin-top: 13px;
  }

  .challenge-grid {
    grid-template-columns: 1fr;
  }

  .notice {
    align-items: flex-start;
    flex-direction: column;
  }

  .notice-link {
    margin-left: 0;
  }

  .empty-state {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .empty-state a {
    width: 100%;
    margin-left: 38px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .dashboard,
  .automation-status.running .automation-pulse,
  .challenge-skeleton {
    animation: none;
  }

  .challenge-card {
    transition: none;
  }
}
</style>
