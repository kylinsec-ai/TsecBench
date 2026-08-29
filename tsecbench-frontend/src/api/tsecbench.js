import { settings } from './settings'

export class APIError extends Error {
  constructor(status, code, message, detail = {}) {
    super(message)
    this.status = status
    this.code = code
    this.detail = detail
  }
}

function normalizeBase(url) {
  return String(url || '').replace(/\/+$/, '')
}

async function request(path, options = {}) {
  const url = normalizeBase(settings.baseUrl) + path
  const headers = {
    BENCHMARK_TOKEN: settings.token,
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {}),
  }
  let response
  try {
    response = await fetch(url, { ...options, headers })
  } catch (err) {
    throw new APIError(0, 'network_error', `无法连接平台: ${err.message}`)
  }
  let payload = null
  try {
    payload = await response.json()
  } catch {
    /* 非 JSON 响应 */
  }
  if (!response.ok) {
    if (payload && payload.code) {
      throw new APIError(response.status, payload.code, payload.message, payload.detail)
    }
    if (payload && Array.isArray(payload.detail)) {
      throw new APIError(
        response.status,
        'validation_error',
        '参数校验失败: ' + JSON.stringify(payload.detail)
      )
    }
    throw new APIError(response.status, 'http_error', `HTTP ${response.status}`)
  }
  return payload
}

export const api = {
  listChallenges: () => request('/openapi/v1/challenges'),
  startChallenge: (uniqueCode) =>
    request(`/openapi/v1/challenges/start?unique_code=${encodeURIComponent(uniqueCode)}`, {
      method: 'POST',
    }),
  getHint: (uniqueCode) =>
    request(`/openapi/v1/challenges/hint?unique_code=${encodeURIComponent(uniqueCode)}`),
  submitFlag: (uniqueCode, flag) =>
    request('/openapi/v1/challenges/submit', {
      method: 'POST',
      body: JSON.stringify({ unique_code: uniqueCode, flag }),
    }),
  closeChallenge: (uniqueCode) =>
    request(`/openapi/v1/challenges/close?unique_code=${encodeURIComponent(uniqueCode)}`, {
      method: 'POST',
    }),
  vpnStatus: () => request('/openapi/v1/vpn/status'),
  vpnUpload: (content) =>
    request('/openapi/v1/vpn/config', {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  vpnStart: () => request('/openapi/v1/vpn/start', { method: 'POST' }),
  vpnStop: () => request('/openapi/v1/vpn/stop', { method: 'POST' }),
}
