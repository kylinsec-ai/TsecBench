<script setup>
import { ref } from 'vue'
import { settings, llmReady } from '../api/settings'
import { api } from '../api/tsecbench'
import { askLLM } from '../api/llm'

const result = ref('')
const resultType = ref('')

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
  <div class="panel">
    <h1 class="title">设置</h1>
    <p class="subtitle">配置自动保存到浏览器本地。所有值需在 TSecBench 平台创建跑分任务后获取。</p>

    <section>
      <h2>平台连接</h2>
      <div class="field">
        <label>BENCHMARK_BASE_URL（平台地址）</label>
        <input v-model="settings.baseUrl" type="text" placeholder="http://127.0.0.1:8000" />
      </div>
      <div class="field">
        <label>BENCHMARK_TOKEN（跑分任务 Token）</label>
        <input v-model="settings.token" type="password" placeholder="UUID" autocomplete="off" />
      </div>
      <button class="primary" @click="testPlatform">测试平台连接</button>
    </section>

    <section>
      <h2>AI 解题（OpenAI 兼容接口）</h2>
      <div class="field">
        <label>LLM Base URL</label>
        <input v-model="settings.llmBaseUrl" type="text" placeholder="https://api.deepseek.com/v1" />
      </div>
      <div class="field">
        <label>LLM API Key</label>
        <input v-model="settings.llmApiKey" type="password" placeholder="sk-..." autocomplete="off" />
      </div>
      <div class="field">
        <label>模型</label>
        <input v-model="settings.llmModel" type="text" placeholder="deepseek-chat" />
      </div>
      <button class="primary" @click="testLLM">测试 LLM 连接</button>
    </section>

    <section>
      <h2>解题行为</h2>
      <div class="field row">
        <label class="check">
          <input v-model="settings.useHint" type="checkbox" />
          自动获取提示（会扣分）
        </label>
      </div>
      <div class="field">
        <label>AI 最大轮数</label>
        <input v-model.number="settings.maxRounds" type="number" min="1" max="50" />
      </div>
      <div class="field row">
        <label class="check">
          <input v-model="settings.autoClose" type="checkbox" />
          解题结束后自动关闭容器
        </label>
      </div>
    </section>

    <div v-if="result" class="result mono" :class="`r-${resultType}`">{{ result }}</div>
  </div>
</template>

<style scoped>
.title {
  font-size: 20px;
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text-dim);
  margin: 0 0 20px;
  font-size: 13px;
}

section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}

section:last-of-type {
  border-bottom: none;
}

h2 {
  font-size: 15px;
  margin: 0 0 12px;
}

.field {
  margin-bottom: 12px;
  max-width: 520px;
}

.field label {
  display: block;
  color: var(--text-dim);
  font-size: 12px;
  margin-bottom: 6px;
}

.field.row {
  display: flex;
  align-items: center;
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text) !important;
  cursor: pointer;
}

.check input {
  width: auto;
}

.result {
  margin-top: 16px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 13px;
}

.r-success {
  color: var(--green);
  border-color: var(--green);
}

.r-error {
  color: var(--red);
  border-color: var(--red);
}

.r-info {
  color: var(--text-dim);
}
</style>
