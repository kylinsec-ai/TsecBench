<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/tsecbench'
import { createSolveSession } from '../composables/useSolver'

const props = defineProps({
  uniqueCode: { type: String, required: true },
})

const router = useRouter()
const controller = ref(null)
const notFound = ref(false)
const error = ref('')
const manualFlag = ref('')
const logBox = ref(null)

async function init() {
  error.value = ''
  notFound.value = false
  try {
    const list = await api.listChallenges()
    const challenge = list.find((item) => item.unique_code === props.uniqueCode)
    if (!challenge) {
      notFound.value = true
      return
    }
    controller.value = createSolveSession(challenge)
  } catch (err) {
    error.value = `加载失败 [${err.code || err.status}]: ${err.message}`
  }
}

onMounted(init)

watch(
  () => props.uniqueCode,
  () => init()
)

const session = computed(() => controller.value?.session || null)

const progress = computed(() =>
  session.value
    ? Math.min(100, Math.round((session.value.correctCount / Math.max(1, session.value.totalFlags)) * 100))
    : 0
)

const statusMeta = computed(() => {
  const status = session.value?.containerStatus
  const labels = {
    available: { label: '已就绪', tone: 'ready', note: '目标地址可通过靶场 VPN 访问。' },
    pending: { label: '启动中', tone: 'warming', note: '实例正在准备，地址出现后即可访问。' },
    stop_pending: { label: '停止中', tone: 'warming', note: '正在释放实例资源。' },
    stopped: { label: '已停止', tone: 'quiet', note: '启动容器后显示新的目标地址。' },
  }
  return labels[status] || { label: '未知状态', tone: 'quiet', note: '等待平台返回容器状态。' }
})

function difficultyLabel(difficulty) {
  const labels = { easy: 'EASY', medium: 'MEDIUM', hard: 'HARD' }
  return labels[String(difficulty || '').toLowerCase()] || String(difficulty || 'UNKNOWN').toUpperCase()
}

watch(
  () => session.value?.logs.length || 0,
  async () => {
    await nextTick()
    if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
  }
)

function pushLog(type, text) {
  if (!session.value) return
  session.value.logs.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    type,
    text,
  })
}

async function run(method, label) {
  if (!controller.value) return
  try {
    await method()
  } catch (err) {
    pushLog('error', `${label}失败 [${err.code || err.status}]: ${err.message}`)
  }
}

async function submitManual() {
  const flag = manualFlag.value.trim()
  if (!flag || !controller.value) return
  try {
    const res = await api.submitFlag(session.value.uniqueCode, flag)
    session.value.submissions.push({ flag, correct: res.correct, awarded: res.awarded })
    if (res.correct) {
      session.value.correctCount = res.correct_flag_count
      session.value.cumulativeScore = res.cumulative_score
      if (res.correct_flag_count >= res.total_flag_count) session.value.completed = true
      pushLog('success', `√ 正确: ${flag} (+${res.awarded}) 累计 ${res.cumulative_score}`)
    } else {
      pushLog('error', `× 错误: ${flag}`)
    }
    manualFlag.value = ''
  } catch (err) {
    pushLog('error', `提交失败 [${err.code || err.status}]: ${err.message}`)
  }
}
</script>

<template>
  <div v-if="error" class="run-error" role="alert">
    <div><span class="eyebrow mono">PLATFORM RESPONSE</span><strong>{{ error }}</strong></div>
    <button class="quiet-button small" @click="router.push('/')">返回 Dashboard</button>
  </div>

  <div v-else-if="notFound" class="run-error" role="alert">
    <div><span class="eyebrow mono">CHALLENGE NOT FOUND</span><strong>未找到题目：{{ uniqueCode }}</strong></div>
    <button class="quiet-button small" @click="router.push('/')">返回 Dashboard</button>
  </div>

  <template v-else-if="session">
    <div class="run-view">
      <header class="run-hero">
        <div class="run-hero-copy">
          <button class="back-link" type="button" @click="router.push('/')">← 返回 Dashboard</button>
          <p class="eyebrow mono">CHALLENGE WORKSPACE / ACTIVE RUN</p>
          <div class="run-title-row">
            <h1 class="run-title mono">{{ session.uniqueCode }}</h1>
            <span class="level-pill">{{ difficultyLabel(session.challenge.difficulty) }} · LV.{{ session.challenge.level }}</span>
          </div>
          <p class="run-description">{{ session.challenge.description || '暂无描述，使用目标地址与运行日志建立解题上下文。' }}</p>
        </div>
        <div class="score-card">
          <span class="score-label mono">COLLECTED SCORE</span>
          <strong>{{ session.cumulativeScore || 0 }}</strong>
          <span class="score-detail mono">{{ session.correctCount }} / {{ session.totalFlags }} FLAGS</span>
        </div>
      </header>

      <section class="runtime-banner" :class="`tone-${statusMeta.tone}`">
        <div class="runtime-state">
          <span class="state-dot" aria-hidden="true"></span>
          <div>
            <span class="eyebrow mono">CONTAINER LIFECYCLE</span>
            <strong>{{ statusMeta.label }}</strong>
            <small>{{ statusMeta.note }}</small>
          </div>
        </div>
        <div class="target-block">
          <span class="eyebrow mono">TARGET / VPN</span>
          <div v-if="session.addresses.length" class="target-links">
            <a
              v-for="address in session.addresses"
              :key="address"
              :href="`http://${address}`"
              target="_blank"
              rel="noopener"
            >{{ address }} ↗</a>
          </div>
          <span v-else class="target-empty mono">启动容器后显示入口地址</span>
        </div>
        <div class="flag-summary">
          <div class="flag-summary-head"><span class="eyebrow mono">FLAG PROGRESS</span><strong>{{ progress }}%</strong></div>
          <div class="progress-track"><span :style="{ width: progress + '%' }"></span></div>
          <span class="flag-summary-detail mono">{{ session.correctCount }} / {{ session.totalFlags }} captured</span>
        </div>
      </section>

      <div class="run-layout">
        <main class="run-main">
          <section class="action-rack">
            <div class="rack-head">
              <div><p class="eyebrow mono">NEXT MOVE</p><h2>选择下一步</h2></div>
              <span v-if="session.busy" class="busy-state mono">PROCESSING...</span>
              <span v-else class="rack-note">先确保目标可访问，再提交答案。</span>
            </div>
            <div class="action-grid">
              <button
                class="action-button"
                :disabled="session.containerStatus === 'available' || session.busy"
                @click="run(() => controller.start(), '启动')"
              >
                <span class="action-glyph" aria-hidden="true">→</span>
                <span><b>启动容器</b><small>OPEN TARGET</small></span>
              </button>
              <button
                class="action-button action-hint"
                :disabled="session.completed || session.hintViewed || session.busy"
                @click="run(() => controller.fetchHint(), '获取提示')"
              >
                <span class="action-glyph" aria-hidden="true">?</span>
                <span><b>{{ session.hintViewed ? '已查看提示' : '获取提示' }}</b><small>会影响后续得分</small></span>
              </button>
              <button
                class="action-button action-ai"
                :disabled="session.busy || session.completed"
                @click="run(() => controller.solveRound(), 'AI 解题')"
              >
                <span class="action-glyph" aria-hidden="true">AI</span>
                <span><b>AI 解题一轮</b><small>ONE ROUND</small></span>
              </button>
              <button
                class="action-button action-ai action-ai-strong"
                :disabled="session.busy || session.completed"
                @click="run(() => controller.autoSolve(), '自动通关')"
              >
                <span class="action-glyph" aria-hidden="true">✦</span>
                <span><b>AI 自动通关</b><small>RUN TO COMPLETE</small></span>
              </button>
              <button
                class="action-button action-danger"
                :disabled="session.containerStatus !== 'available' || session.busy"
                @click="run(() => controller.close(), '关闭')"
              >
                <span class="action-glyph" aria-hidden="true">×</span>
                <span><b>关闭容器</b><small>RELEASE RESOURCE</small></span>
              </button>
            </div>
            <div class="manual-submit">
              <div><span class="eyebrow mono">MANUAL FLAG SUBMISSION</span><small>直接提交你在目标中找到的答案。</small></div>
              <div class="manual-form">
                <label class="sr-only" for="manual-flag">手动提交 flag</label>
                <input
                  id="manual-flag"
                  v-model="manualFlag"
                  type="text"
                  placeholder="flag{...}"
                  :disabled="session.busy"
                  @keyup.enter="submitManual"
                />
                <button class="primary" :disabled="!manualFlag.trim() || session.busy" @click="submitManual">提交 flag</button>
              </div>
            </div>
          </section>

          <section v-if="session.hintViewed" class="hint-panel" role="status">
            <div class="hint-mark">!</div>
            <div><span class="eyebrow mono">HINT / SCORE IMPACT</span><p>{{ session.hint || '该题没有可用提示。' }}</p></div>
          </section>

          <section v-if="session.submissions.length" class="history-panel">
            <div class="section-head"><div><p class="eyebrow mono">EVIDENCE LEDGER</p><h2>提交记录</h2></div><span class="section-count mono">{{ session.submissions.length }} attempts</span></div>
            <div class="submission-list">
              <div v-for="(submission, index) in session.submissions" :key="index" class="submission-row">
                <span class="submission-index mono">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="submission-flag mono">{{ submission.flag }}</span>
                <span class="submission-result" :class="submission.correct ? 'correct' : 'incorrect'">{{ submission.correct ? 'CORRECT' : 'REJECTED' }}</span>
                <span class="submission-score mono">{{ submission.correct ? `+${submission.awarded}` : '—' }}</span>
              </div>
            </div>
          </section>
        </main>

        <aside class="log-panel">
          <div class="section-head"><div><p class="eyebrow mono">LIVE OUTPUT</p><h2>操作日志</h2></div><span class="log-live mono">● LIVE</span></div>
          <div ref="logBox" class="log-body mono" aria-live="polite">
            <div v-for="(log, index) in session.logs" :key="index" class="log-line" :class="`log-${log.type}`">
              <span class="log-time">{{ log.time }}</span>{{ log.text }}
            </div>
            <div v-if="!session.logs.length" class="dim">暂无日志。完成一次操作后，平台响应会显示在这里。</div>
          </div>
        </aside>
      </div>
    </div>
  </template>
</template>

<style scoped>
.run-view {
  animation: run-in 420ms ease both;
}

.eyebrow {
  margin: 0;
  color: var(--text-dim);
  font-size: 9px;
  letter-spacing: 0.14em;
  line-height: 1.3;
}

.run-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.run-hero-copy {
  min-width: 0;
  max-width: 760px;
}

.back-link {
  margin-bottom: 24px;
  padding: 0;
  color: var(--text-dim);
  background: transparent;
  border: 0;
  font: 10px/1 var(--mono);
}

.back-link:hover {
  color: var(--accent);
  border: 0;
  transform: none;
}

.run-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 9px;
}

.run-title {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--text);
  font-size: clamp(23px, 3vw, 36px);
  font-weight: 500;
  letter-spacing: -0.05em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.level-pill {
  padding: 5px 8px;
  color: var(--accent);
  border: 1px solid rgba(145, 226, 208, 0.5);
  font: 9px/1 var(--mono);
}

.run-description {
  max-width: 650px;
  margin: 12px 0 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.score-card {
  min-width: 160px;
  padding: 15px 17px;
  background: rgba(23, 26, 42, 0.8);
  border: 1px solid var(--border);
  border-top-color: var(--ai);
}

.score-label,
.score-detail {
  display: block;
  color: var(--text-dim);
  font-size: 9px;
}

.score-card strong {
  display: block;
  margin: 9px 0 7px;
  color: var(--text);
  font: 500 34px/1 var(--display);
  letter-spacing: -0.06em;
}

.runtime-banner {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(200px, 1.1fr) minmax(150px, 0.75fr);
  align-items: center;
  gap: 18px;
  padding: 18px;
  background: rgba(23, 26, 42, 0.82);
  border: 1px solid var(--border);
  border-left: 3px solid var(--text-dim);
}

.runtime-banner.tone-ready {
  border-left-color: var(--accent);
}

.runtime-banner.tone-warming {
  border-left-color: var(--warning);
}

.runtime-state,
.target-block,
.flag-summary {
  min-width: 0;
}

.runtime-state {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.state-dot {
  width: 9px;
  height: 9px;
  flex: 0 0 auto;
  margin-top: 3px;
  border-radius: 50%;
  background: var(--text-dim);
}

.tone-ready .state-dot {
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(145, 226, 208, 0.12);
}

.tone-warming .state-dot {
  background: var(--warning);
  animation: status-pulse 1.6s ease-in-out infinite;
}

.runtime-state strong,
.runtime-state small {
  display: block;
}

.runtime-state strong {
  margin-top: 5px;
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.runtime-state small {
  margin-top: 4px;
  color: var(--text-dim);
  font-size: 10px;
}

.target-block {
  padding-left: 18px;
  border-left: 1px solid var(--border);
}

.target-links {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 12px;
  margin-top: 8px;
}

.target-links a,
.target-empty {
  color: var(--accent);
  font-size: 11px;
}

.target-empty {
  display: block;
  margin-top: 8px;
  color: var(--text-dim);
  font-size: 9px;
}

.flag-summary {
  padding-left: 18px;
  border-left: 1px solid var(--border);
}

.flag-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.flag-summary-head strong {
  color: var(--accent);
  font: 14px/1 var(--mono);
}

.progress-track {
  height: 4px;
  margin-top: 11px;
  overflow: hidden;
  background: #343a56;
}

.progress-track span {
  display: block;
  height: 100%;
  background: var(--accent);
  transition: width 260ms ease;
}

.flag-summary-detail {
  display: block;
  margin-top: 7px;
  color: var(--text-dim);
  font-size: 9px;
}

.run-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  align-items: start;
  gap: 22px;
  margin-top: 22px;
}

.run-main {
  min-width: 0;
}

.action-rack,
.history-panel,
.log-panel {
  background: rgba(23, 26, 42, 0.78);
  border: 1px solid var(--border);
}

.action-rack {
  padding: 19px;
}

.rack-head,
.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.action-rack h2,
.history-panel h2,
.log-panel h2 {
  margin: 5px 0 0;
  color: var(--text);
  font: 600 19px/1 var(--display);
  letter-spacing: -0.04em;
}

.rack-note,
.busy-state,
.section-count,
.log-live {
  color: var(--text-dim);
  font: 9px/1.4 var(--mono);
}

.busy-state,
.log-live {
  color: var(--ai);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 18px;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 68px;
  padding: 11px 12px;
  color: var(--text);
  text-align: left;
  background: rgba(14, 17, 32, 0.66);
  border-color: var(--border);
}

.action-button:hover:not(:disabled) {
  background: rgba(30, 36, 56, 0.9);
}

.action-button:first-child {
  border-left: 3px solid var(--accent);
}

.action-glyph {
  width: 25px;
  height: 25px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--accent);
  border: 1px solid rgba(145, 226, 208, 0.42);
  font: 11px/1 var(--mono);
}

.action-button b,
.action-button small {
  display: block;
}

.action-button b {
  font-size: 12px;
  font-weight: 600;
}

.action-button small {
  margin-top: 4px;
  color: var(--text-dim);
  font: 8px/1 var(--mono);
}

.action-hint {
  border-left: 3px solid var(--warning);
}

.action-hint .action-glyph {
  color: var(--warning);
  border-color: rgba(241, 199, 124, 0.44);
}

.action-ai {
  border-left: 3px solid var(--ai);
}

.action-ai .action-glyph {
  color: var(--ai);
  border-color: rgba(139, 124, 255, 0.46);
}

.action-ai-strong {
  background: rgba(139, 124, 255, 0.08);
}

.action-danger {
  border-left: 3px solid var(--risk);
}

.action-danger .action-glyph {
  color: var(--risk);
  border-color: rgba(255, 149, 126, 0.44);
}

.manual-submit {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 14px;
  margin-top: 17px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.manual-submit > div:first-child {
  display: grid;
  gap: 5px;
}

.manual-submit small {
  color: var(--text-dim);
  font-size: 10px;
}

.manual-form {
  display: flex;
  flex: 1;
  gap: 7px;
  max-width: 430px;
}

.manual-form input {
  min-width: 0;
}

.hint-panel {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-top: 12px;
  padding: 14px 16px;
  background: rgba(241, 199, 124, 0.05);
  border: 1px solid rgba(241, 199, 124, 0.46);
}

.hint-mark {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--warning);
  border: 1px solid var(--warning);
  border-radius: 50%;
  font: 10px/1 var(--mono);
}

.hint-panel p {
  margin: 6px 0 0;
  color: var(--text);
  font: 11px/1.65 var(--mono);
  word-break: break-word;
}

.history-panel {
  margin-top: 22px;
  padding: 18px;
}

.section-head {
  align-items: center;
}

.submission-list {
  margin-top: 15px;
  border-top: 1px solid var(--border);
}

.submission-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 80px 48px;
  align-items: center;
  gap: 9px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(52, 58, 86, 0.72);
  font-size: 11px;
}

.submission-index {
  color: var(--text-dim);
  font-size: 9px;
}

.submission-flag {
  overflow: hidden;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submission-result {
  font: 9px/1 var(--mono);
}

.submission-result.correct {
  color: var(--accent);
}

.submission-result.incorrect {
  color: var(--risk);
}

.submission-score {
  color: var(--text-dim);
  text-align: right;
  font-size: 10px;
}

.log-panel {
  position: sticky;
  top: 94px;
  min-width: 0;
  padding: 18px;
  background: rgba(10, 12, 22, 0.82);
}

.log-live {
  color: var(--accent);
  font-size: 8px;
}

.log-body {
  min-height: 310px;
  max-height: 520px;
  overflow-y: auto;
  margin-top: 16px;
  padding-top: 13px;
  border-top: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 10px;
  line-height: 1.8;
}

.log-line {
  word-break: break-word;
}

.log-time {
  display: inline-block;
  min-width: 61px;
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

.run-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px;
  background: rgba(255, 149, 126, 0.05);
  border: 1px solid rgba(255, 149, 126, 0.55);
}

.run-error > div {
  display: grid;
  gap: 5px;
}

.run-error strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
}

@keyframes run-in {
  from { opacity: 0; transform: translateY(7px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes status-pulse {
  50% { opacity: 0.4; transform: scale(0.75); }
}

@media (max-width: 1060px) {
  .run-layout {
    grid-template-columns: minmax(0, 1fr) 270px;
  }

  .runtime-banner {
    grid-template-columns: 1fr 1fr;
  }

  .flag-summary {
    grid-column: 1 / -1;
    padding-top: 14px;
    padding-left: 0;
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}

@media (max-width: 820px) {
  .run-hero {
    display: block;
  }

  .score-card {
    width: 100%;
    margin-top: 17px;
  }

  .score-card strong {
    display: inline-block;
    margin-right: 9px;
  }

  .score-detail {
    display: inline-block;
  }

  .run-layout {
    display: block;
  }

  .log-panel {
    position: static;
    margin-top: 22px;
  }
}

@media (max-width: 620px) {
  .runtime-banner {
    display: block;
  }

  .target-block,
  .flag-summary {
    margin-top: 17px;
    padding-top: 17px;
    padding-left: 0;
    border-top: 1px solid var(--border);
    border-left: 0;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }

  .manual-submit {
    display: block;
  }

  .manual-form {
    max-width: none;
    margin-top: 11px;
  }

  .submission-row {
    grid-template-columns: 26px minmax(0, 1fr) 66px;
  }

  .submission-score {
    display: none;
  }

  .run-error {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .run-view,
  .tone-warming .state-dot {
    animation: none;
  }

  .progress-track span {
    transition: none;
  }
}
</style>
