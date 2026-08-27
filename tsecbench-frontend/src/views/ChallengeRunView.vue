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
    const challenge = list.find((c) => c.unique_code === props.uniqueCode)
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
    ? Math.round((session.value.correctCount / Math.max(1, session.value.totalFlags)) * 100)
    : 0
)

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
  <div v-if="error" class="panel error-box">
    <span>{{ error }}</span>
    <button class="small" @click="router.push('/')">返回列表</button>
  </div>

  <div v-else-if="notFound" class="panel error-box">
    <span>未找到题目: {{ uniqueCode }}</span>
    <button class="small" @click="router.push('/')">返回列表</button>
  </div>

  <template v-else-if="session">
    <div class="toolbar">
      <div>
        <button class="back" @click="router.push('/')">← 返回</button>
        <h1 class="title mono">{{ session.uniqueCode }}</h1>
        <p class="subtitle">{{ session.challenge.description || '（无描述）' }}</p>
      </div>
      <div class="score-box panel mono">
        <span>得分 {{ session.cumulativeScore || 0 }}</span>
        <span>{{ session.correctCount }}/{{ session.totalFlags }} flag</span>
        <span class="badge" :class="session.challenge.difficulty">
          {{ session.challenge.difficulty }} · Lv.{{ session.challenge.level }}
        </span>
      </div>
    </div>

    <div class="panel status-line">
      <span>
        容器状态:
        <b class="mono" :class="`status-${session.containerStatus}`">{{ session.containerStatus }}</b>
      </span>
      <span v-if="session.addresses.length" class="mono addr">
        目标:
        <a
          v-for="a in session.addresses"
          :key="a"
          :href="`http://${a}`"
          target="_blank"
          rel="noopener"
        >{{ a }}</a>
      </span>
      <span v-else class="dim">目标地址需先启动容器</span>
    </div>

    <div class="progress-wrap">
      <div class="progress" :style="{ width: progress + '%' }"></div>
    </div>

    <div class="actions panel">
      <button
        :disabled="session.containerStatus === 'available' || session.busy"
        @click="run(() => controller.start(), '启动')"
      >启动容器</button>
      <button
        :disabled="session.completed || session.hintViewed || session.busy"
        @click="run(() => controller.fetchHint(), '获取提示')"
      >获取提示</button>
      <button
        class="primary"
        :disabled="session.busy || session.completed"
        @click="run(() => controller.solveRound(), 'AI 解题')"
      >AI 解题一轮</button>
      <button
        class="primary"
        :disabled="session.busy || session.completed"
        @click="run(() => controller.autoSolve(), '自动通关')"
      >AI 自动通关</button>
      <button
        :disabled="session.containerStatus !== 'available' || session.busy"
        @click="run(() => controller.close(), '关闭')"
      >关闭容器</button>
      <div class="manual">
        <input
          v-model="manualFlag"
          type="text"
          placeholder="手动提交 flag..."
          :disabled="session.busy"
          @keyup.enter="submitManual"
        />
        <button :disabled="!manualFlag.trim() || session.busy" @click="submitManual">提交</button>
      </div>
    </div>

    <div v-if="session.hint" class="panel hint-box mono">
      提示: {{ session.hint }}
    </div>

    <div v-if="session.submissions.length" class="panel submissions">
      <h3 class="mono">提交记录</h3>
      <table>
        <thead>
          <tr><th>flag</th><th>结果</th><th>得分</th></tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in session.submissions" :key="i">
            <td class="mono">{{ s.flag }}</td>
            <td :class="s.correct ? 'ok' : 'bad'">{{ s.correct ? '√ 正确' : '× 错误' }}</td>
            <td class="mono">{{ s.awarded }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel logs">
      <h3 class="mono">操作日志</h3>
      <div ref="logBox" class="log-body mono">
        <div v-for="(l, i) in session.logs" :key="i" class="log-line" :class="`log-${l.type}`">
          <span class="log-time">{{ l.time }}</span> {{ l.text }}
        </div>
        <div v-if="!session.logs.length" class="dim">暂无日志</div>
      </div>
    </div>
  </template>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.back {
  margin-bottom: 8px;
  color: var(--text-dim);
  border: none;
  background: none;
  padding: 0;
  font-size: 13px;
}

.title {
  font-size: 20px;
  margin: 0;
}

.subtitle {
  color: var(--text-dim);
  margin: 4px 0 0;
}

.score-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text-dim);
  min-width: 150px;
}

.status-line {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.addr {
  display: flex;
  gap: 10px;
}

.progress-wrap {
  height: 8px;
  background: var(--bg);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress {
  height: 100%;
  background: var(--green);
  border-radius: 999px;
  transition: width 0.3s;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.manual {
  display: flex;
  gap: 8px;
  flex: 1;
  min-width: 260px;
}

.hint-box {
  border-color: var(--yellow);
  color: var(--yellow);
  margin-bottom: 12px;
}

.submissions {
  margin-bottom: 12px;
}

.submissions h3,
.logs h3 {
  margin: 0 0 10px;
  font-size: 13px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

th {
  color: var(--text-dim);
  font-weight: 400;
  font-size: 12px;
}

.ok {
  color: var(--green);
}

.bad {
  color: var(--red);
}

.logs {
  background: #0a0d12;
}

.log-body {
  max-height: 320px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.8;
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

.error-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-color: var(--red);
  color: var(--red);
}

.dim {
  color: var(--text-dim);
}
</style>
