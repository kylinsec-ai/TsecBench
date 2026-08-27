<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/tsecbench'
import { settingsReady } from '../api/settings'
import { createSolveSession } from '../composables/useSolver'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const error = ref('')
const autoRunning = ref(false)
const showLog = ref(false)
const autoLogs = ref([])

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

function difficultyClass(d) {
  return String(d || '').toLowerCase()
}

function openChallenge(code) {
  router.push({ path: `/challenges/${encodeURIComponent(code)}` })
}

async function autoRunOne(challenge) {
  const session = createSolveSession(challenge)
  await session.autoSolve()
  session.session.logs.forEach((l) =>
    autoLogs.value.push({ time: l.time, type: l.type, text: `[${session.uniqueCode}] ${l.text}` })
  )
  await load()
}

async function autoRunAll() {
  if (autoRunning.value) return
  if (!settingsReady()) {
    autoLogs.value.push({ time: now(), type: 'error', text: '请先在「设置」中配置平台地址与 Token' })
    showLog.value = true
    return
  }
  autoRunning.value = true
  showLog.value = true
  autoLogs.value = []
  try {
    const targets = list.value.filter((c) => !c.is_completed)
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
  <div>
    <div class="toolbar">
      <div>
        <h1 class="title">题目列表</h1>
        <p class="subtitle">点击题目进入 AI 解题页；或批量自动解。</p>
      </div>
      <div class="actions">
        <button :disabled="loading" @click="load">刷新</button>
        <button class="primary" :disabled="autoRunning" @click="autoRunAll">
          {{ autoRunning ? '自动解题中...' : '全部自动解' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="panel error-box">
      <span>{{ error }}</span>
      <button class="small" @click="router.push('/settings')">去设置</button>
    </div>

    <div v-if="loading && !list.length" class="panel dim">加载中...</div>

    <div v-else-if="list.length" class="grid">
      <article
        v-for="c in list"
        :key="c.unique_code"
        class="card"
        :class="{ done: c.is_completed }"
        @click="openChallenge(c.unique_code)"
      >
        <header class="card-head">
          <span class="mono code">{{ c.unique_code }}</span>
          <span class="badge" :class="difficultyClass(c.difficulty)">{{ c.difficulty }}</span>
        </header>
        <p class="desc">{{ c.description || '（无描述）' }}</p>
        <div class="meta mono">
          <span>Lv.{{ c.level }}</span>
          <span>{{ c.total_score }} 分</span>
          <span class="status" :class="`status-${c.container_status}`">{{ c.container_status }}</span>
        </div>
        <div class="progress-wrap">
          <div
            class="progress"
            :style="{ width: (c.correct_flag_count / Math.max(1, c.flag_count)) * 100 + '%' }"
          ></div>
        </div>
        <div class="progress-label mono">
          <span>{{ c.correct_flag_count }}/{{ c.flag_count }} flag</span>
          <span class="done-mark" v-if="c.is_completed">已通关</span>
          <span v-else class="dim">未通关</span>
        </div>
        <div v-if="c.container_addr && c.container_addr.length" class="addr mono">
          {{ c.container_addr.join(', ') }}
        </div>
      </article>
    </div>

    <div v-else-if="!loading" class="panel dim">
      暂无题目。请确认 Token 与平台地址，或在后端 seed 任务。
    </div>

    <div v-if="showLog" class="log-drawer">
      <div class="log-head">
        <span class="mono">自动解题日志</span>
        <button class="small" @click="showLog = false">收起</button>
      </div>
      <div class="log-body mono">
        <div v-for="(l, i) in autoLogs" :key="i" class="log-line" :class="`log-${l.type}`">
          <span class="log-time">{{ l.time }}</span> {{ l.text }}
        </div>
        <div v-if="!autoLogs.length" class="dim">暂无日志</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.title {
  font-size: 20px;
  margin: 0;
}

.subtitle {
  color: var(--text-dim);
  margin: 4px 0 0;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
}

.error-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-color: var(--red);
  color: var(--red);
  margin-bottom: 16px;
}

.dim {
  color: var(--text-dim);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.card.done {
  opacity: 0.6;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.code {
  font-weight: 700;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desc {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  min-height: 36px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-dim);
}

.progress-wrap {
  height: 6px;
  background: var(--bg);
  border-radius: 999px;
  overflow: hidden;
}

.progress {
  height: 100%;
  background: var(--green);
  border-radius: 999px;
  transition: width 0.3s;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.done-mark {
  color: var(--green);
}

.addr {
  font-size: 12px;
  color: var(--accent);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-drawer {
  margin-top: 20px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-panel);
  overflow: hidden;
}

.log-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}

.log-body {
  max-height: 280px;
  overflow-y: auto;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.7;
}

.log-line {
  word-break: break-all;
}

.log-time {
  color: var(--text-dim);
  margin-right: 8px;
}

.log-success {
  color: var(--green);
}

.log-error {
  color: var(--red);
}

.log-warn {
  color: var(--yellow);
}

.log-info,
.log-api {
  color: var(--text);
}
</style>
