import { reactive, watch } from 'vue'

const STORAGE_KEY = 'tsecbench.settings.v1'

const defaults = {
  baseUrl: 'http://localhost:5173',
  token: '',
  llmBaseUrl: 'https://api.deepseek.com/v1',
  llmApiKey: '',
  llmModel: 'deepseek-chat',
  useHint: false,
  maxRounds: 6,
  autoClose: true,
}

function load() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return { ...defaults, ...raw }
  } catch {
    return { ...defaults }
  }
}

export const settings = reactive(load())

watch(
  settings,
  (value) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  },
  { deep: true }
)

export function settingsReady() {
  return Boolean(settings.baseUrl && settings.token)
}

export function llmReady() {
  return Boolean(settings.llmBaseUrl && settings.llmApiKey && settings.llmModel)
}
