import { settings } from './settings'

export async function askLLM(messages) {
  const url = String(settings.llmBaseUrl || '').replace(/\/+$/, '') + '/chat/completions'
  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${settings.llmApiKey}`,
      },
      body: JSON.stringify({
        model: settings.llmModel,
        messages,
        temperature: 0.3,
        max_tokens: 4096,
      }),
    })
  } catch (err) {
    throw new Error(`LLM 请求失败: ${err.message}`)
  }
  let payload = null
  try {
    payload = await response.json()
  } catch {
    /* 非 JSON 响应 */
  }
  if (!response.ok) {
    const detail =
      payload && payload.error && payload.error.message
        ? payload.error.message
        : `HTTP ${response.status}`
    throw new Error(`LLM 接口错误: ${detail}`)
  }
  const content = payload?.choices?.[0]?.message?.content ?? ''
  if (!content) throw new Error('LLM 返回空内容')
  return content
}

const FLAG_RE = /flag\{[^}\n]+\}/gi

export function extractFlags(text) {
  if (!text) return []
  const trimmed = String(text).trim()
  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) {
      const flags = parsed
        .filter((x) => typeof x === 'string' && x.trim())
        .map((x) => x.trim())
      if (flags.length) return flags
    }
  } catch {
    /* 不是纯 JSON，继续用正则 */
  }
  const matches = [...new Set(trimmed.match(FLAG_RE) || [])].map((f) =>
    f.replace(/^flag/i, 'flag')
  )
  if (matches.length) return matches
  const candidates = []
  for (const line of trimmed.split(/\r?\n/)) {
    const m = line.match(/flag\s*[=:：]\s*(.+)/i)
    if (m) {
      const value = m[1].trim().replace(/[",'；;]+$/g, '')
      if (value && !candidates.includes(value)) candidates.push(value)
    }
  }
  return candidates.slice(0, 10)
}
