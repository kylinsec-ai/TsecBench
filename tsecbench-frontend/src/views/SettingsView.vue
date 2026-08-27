<script setup>
import { computed, ref } from 'vue'
import { settings, llmReady, settingsReady } from '../api/settings'
import { api } from '../api/tsecbench'
import { askLLM } from '../api/llm'

const result = ref('')
const resultType = ref('')
const platformConfigured = computed(() => settingsReady())
const aiConfigured = computed(() => llmReady())

function log(type, text) {
  resultType.value = type
  result.value = text
}

async function testPlatform() {
  log('info', '测试平台连接中...')
  try {
    const list = await api.listChallenges()
    log('success', `平台连接成功，共 ${list.length} 道题`)
  } catch (err) {
    log('error', `平台连接失败 [${err.code || err.status}]: ${err.message}`)
  }
}

async function testLLM() {
  if (!llmReady()) {
    log('error', '请先填写 LLM 地址 / Key / 模型')
    return
  }
  log('info', '测试 LLM 连接中...')
  try {
    await askLLM([
      { role: 'system', content: '你是一个测试助手。' },
      { role: 'user', content: '只回复两个字：正常' },
    ])
    log('success', 'LLM 连接成功')
  } catch (err) {
    log('error', `LLM 连接失败: ${err.message}`)
  }
}
</script>

<template>
  <div class="settings-view">
    <section class="settings-hero">
      <div>
        <p class="eyebrow mono">SYSTEM / CONFIGURATION</p>
        <h1>把连接准备好。</h1>
        <p class="settings-subtitle">配置保存在当前浏览器。平台 Token 和 LLM Key 只用于请求，不会写入项目文件。</p>
      </div>
      <div class="settings-status" :class="{ ready: platformConfigured }">
        <span class="status-dot" aria-hidden="true"></span>
        <div><span class="mono">PLATFORM LINK</span><strong>{{ platformConfigured ? '已就绪' : '等待配置' }}</strong></div>
      </div>
    </section>

    <div class="settings-rule" aria-hidden="true"></div>

    <div class="settings-grid">
      <section class="settings-card settings-platform">
        <div class="card-heading">
          <div><p class="eyebrow mono">01 / BENCHMARK</p><h2>平台连接</h2></div>
          <span class="card-state" :class="{ ready: platformConfigured }">{{ platformConfigured ? 'READY' : 'REQUIRED' }}</span>
        </div>
        <p class="card-description">从跑分任务获取平台地址与 Token。连接成功后，Dashboard 会同步题目与容器状态。</p>
        <div class="field">
          <label for="base-url">BENCHMARK_BASE_URL <span>平台地址</span></label>
          <input id="base-url" v-model="settings.baseUrl" type="text" placeholder="http://127.0.0.1:8000" />
        </div>
        <div class="field">
          <label for="benchmark-token">BENCHMARK_TOKEN <span>跑分任务 Token</span></label>
          <input id="benchmark-token" v-model="settings.token" type="password" placeholder="UUID" autocomplete="off" />
        </div>
        <button class="primary" @click="testPlatform"><span class="button-glyph" aria-hidden="true">↗</span>测试平台连接</button>
      </section>

      <section class="settings-card settings-ai">
        <div class="card-heading">
          <div><p class="eyebrow mono">02 / ASSISTANT</p><h2>AI 解题</h2></div>
          <span class="card-state ai-state" :class="{ ready: aiConfigured }">{{ aiConfigured ? 'READY' : 'OPTIONAL' }}</span>
        </div>
        <p class="card-description">使用 OpenAI 兼容接口生成候选 flag。手动解题不依赖此项。</p>
        <div class="field">
          <label for="llm-url">LLM BASE URL <span>兼容接口地址</span></label>
          <input id="llm-url" v-model="settings.llmBaseUrl" type="text" placeholder="https://api.deepseek.com/v1" />
        </div>
        <div class="field">
          <label for="llm-key">LLM API KEY <span>浏览器本地保存</span></label>
          <input id="llm-key" v-model="settings.llmApiKey" type="password" placeholder="sk-..." autocomplete="off" />
        </div>
        <div class="field">
          <label for="llm-model">MODEL <span>模型名称</span></label>
          <input id="llm-model" v-model="settings.llmModel" type="text" placeholder="deepseek-chat" />
        </div>
        <button class="ai" @click="testLLM"><span class="button-glyph" aria-hidden="true">AI</span>测试 LLM 连接</button>
      </section>

      <section class="settings-card settings-behavior">
        <div class="card-heading">
          <div><p class="eyebrow mono">03 / RUN POLICY</p><h2>解题行为</h2></div>
          <span class="card-state">AUTO-SAVED</span>
        </div>
        <p class="card-description">这些策略只影响 AI 自动解题；每次修改都会自动保存。</p>
        <label class="toggle-row">
          <span><strong>自动获取提示</strong><small>会扣减该题后续得分，默认关闭。</small></span>
          <input v-model="settings.useHint" type="checkbox" />
          <i aria-hidden="true"></i>
        </label>
        <label class="field">
          <span class="field-label">AI 最大轮数 <small>1–50</small></span>
          <input v-model.number="settings.maxRounds" type="number" min="1" max="50" />
        </label>
        <label class="toggle-row">
          <span><strong>解题结束后自动关闭容器</strong><small>释放实例资源，避免占满上限。</small></span>
          <input v-model="settings.autoClose" type="checkbox" />
          <i aria-hidden="true"></i>
        </label>
      </section>
    </div>

    <div v-if="result" class="connection-result" :class="`result-${resultType}`" role="status">
      <span class="result-mark" aria-hidden="true">{{ resultType === 'success' ? '✓' : resultType === 'error' ? '!' : '·' }}</span>
      <span>{{ result }}</span>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 1040px;
  animation: settings-in 420ms ease both;
}

.eyebrow {
  margin: 0;
  color: var(--text-faint);
  font-size: 9px;
  letter-spacing: 0.14em;
  line-height: 1.3;
}

.settings-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.settings-view h1 {
  margin: 10px 0 8px;
  color: var(--text);
  font: 600 clamp(32px, 4vw, 50px)/1 var(--display);
  letter-spacing: -0.06em;
}

.settings-subtitle {
  max-width: 600px;
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.settings-status {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 132px;
  padding: 11px 12px;
  border: 1px solid rgba(208, 67, 58, 0.4);
  border-radius: 8px;
  background: var(--risk-soft);
}

.settings-status.ready {
  border-color: rgba(14, 116, 107, 0.4);
  background: var(--accent-soft);
}

.status-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--risk);
}

.settings-status.ready .status-dot {
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(14, 116, 107, 0.12);
}

.settings-status div {
  display: grid;
  gap: 4px;
}

.settings-status span {
  color: var(--text-faint);
  font-size: 8px;
}

.settings-status strong {
  color: var(--text);
  font-size: 11px;
  font-weight: 500;
}

.settings-rule {
  height: 1px;
  margin: 28px 0 18px;
  background: linear-gradient(90deg, var(--border-strong), rgba(205, 214, 227, 0.08));
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.settings-card {
  padding: 19px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.settings-platform {
  border-top: 3px solid var(--accent);
}

.settings-ai {
  border-top: 3px solid var(--ai);
}

.settings-behavior {
  grid-column: 1 / -1;
  border-top: 3px solid var(--warning);
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.settings-view h2 {
  margin: 5px 0 0;
  color: var(--text);
  font: 600 20px/1 var(--display);
  letter-spacing: -0.04em;
}

.card-state {
  padding: 5px 7px;
  color: var(--text-dim);
  border: 1px solid var(--border-strong);
  border-radius: 5px;
  font: 8px/1 var(--mono);
}

.card-state.ready {
  color: var(--accent);
  border-color: rgba(14, 116, 107, 0.4);
  background: var(--accent-soft);
}

.card-state.ai-state.ready {
  color: var(--ai);
  border-color: rgba(91, 79, 209, 0.5);
  background: var(--ai-soft);
}

.card-description {
  min-height: 40px;
  margin: 14px 0 19px;
  color: var(--text-dim);
  font-size: 11px;
  line-height: 1.65;
}

.field {
  display: block;
  margin-bottom: 13px;
}

.field label,
.field > .field-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
  color: var(--text-dim);
  font: 9px/1 var(--mono);
  letter-spacing: 0.04em;
}

.field label span,
.field-label small {
  color: var(--text-faint);
  font: 9px/1 var(--body);
  letter-spacing: 0;
}

.settings-card button {
  margin-top: 4px;
}

.button-glyph {
  margin-right: 7px;
  color: inherit;
  font: 11px/1 var(--mono);
}

.settings-ai .button-glyph {
  color: #fff;
}

.toggle-row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 0;
  border-top: 1px solid var(--border);
  cursor: pointer;
}

.toggle-row span {
  display: grid;
  gap: 4px;
}

.toggle-row strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
}

.toggle-row small {
  color: var(--text-dim);
  font-size: 10px;
}

.toggle-row input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.toggle-row i {
  position: relative;
  width: 36px;
  height: 20px;
  flex: 0 0 auto;
  display: block;
  background: var(--panel-soft);
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  transition: background 180ms ease, border-color 180ms ease;
}

.toggle-row i::after {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-faint);
  content: '';
  transition: transform 180ms ease, background 180ms ease;
}

.toggle-row input:checked + i {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.toggle-row input:checked + i::after {
  background: var(--accent);
  transform: translateX(16px);
}

.toggle-row input:focus-visible + i {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.settings-behavior .field {
  max-width: 240px;
  margin: 15px 0 2px;
}

.connection-result {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-dim);
  font: 11px/1.5 var(--mono);
}

.result-mark {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-size: 10px;
}

.result-success {
  color: var(--accent);
  border-color: rgba(14, 116, 107, 0.45);
  background: var(--accent-soft);
}

.result-error {
  color: var(--risk);
  border-color: rgba(208, 67, 58, 0.45);
  background: var(--risk-soft);
}

.result-info {
  color: var(--text-dim);
}

@keyframes settings-in {
  from { opacity: 0; transform: translateY(7px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 740px) {
  .settings-hero {
    display: block;
  }

  .settings-status {
    width: fit-content;
    margin-top: 18px;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-behavior {
    grid-column: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .settings-view,
  .toggle-row i,
  .toggle-row i::after {
    animation: none;
    transition: none;
  }
}
</style>
