// All backend calls go through here. In dev, Vite proxies /api to FastAPI (see vite.config.js).
// Set VITE_API_BASE (e.g. http://localhost:8000) only if you serve the frontend separately.
const BASE = import.meta.env.VITE_API_BASE || ''

export class ApiError extends Error {
  constructor(error, detail, status) {
    super(detail || error)
    this.error = error
    this.detail = detail
    this.status = status
  }
}

async function request(path, { method = 'GET', body, form } = {}) {
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: form || (body ? JSON.stringify(body) : undefined),
    })
  } catch {
    throw new ApiError('network_error', 'Cannot reach the LabelGuard server. Is the backend running on port 8000?', 0)
  }
  let data = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    throw new ApiError(data?.error || 'http_error', data?.detail || `Request failed (${res.status})`, res.status)
  }
  return data
}

const q = (member) => (member && member !== 'all' ? `?member=${encodeURIComponent(member)}` : '')

export const api = {
  health: () => request('/api/health'),
  stats: () => request('/api/stats'),
  formula: () => request('/api/score/formula'),

  getProfile: () => request('/api/profile'),
  parseProfile: (text) => request('/api/profile/parse', { method: 'POST', body: { text } }),
  saveProfile: (household, raw_text) => request('/api/profile', { method: 'PUT', body: { household, raw_text } }),

  scanImage: (fileOrFiles) => {
    const form = new FormData()
    const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles]
    files.forEach((f) => form.append('files', f))
    return request('/api/scan', { method: 'POST', form })
  },
  scanBarcode: (barcode) => request('/api/scan/barcode', { method: 'POST', body: { barcode } }),
  scanManual: (extraction) => request('/api/scan/json', { method: 'POST', body: { extraction } }),
  deleteScan: (id) => request(`/api/scan/${id}`, { method: 'DELETE' }),
  ask: (scan_id, question, language) => request('/api/scan/ask', { method: 'POST', body: { scan_id, question, language } }),

  products: (params) => request(`/api/products?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))}`),
  lookup: (q) => request(`/api/lookup?q=${encodeURIComponent(q)}`),
  insights: () => request('/api/insights'),
  allergyCards: () => request('/api/allergy-card'),
  shopping: () => request('/api/shopping'),
  shoppingAdd: (item) => request('/api/shopping', { method: 'POST', body: item }),
  shoppingToggle: (id, done) => request(`/api/shopping/${id}`, { method: 'PATCH', body: { done } }),
  shoppingDelete: (id) => request(`/api/shopping/${id}`, { method: 'DELETE' }),
  deleteLog: (id) => request(`/api/log/${id}`, { method: 'DELETE' }),
  resetDemo: () => request('/api/admin/reset', { method: 'POST' }),
  demoLabels: () => request('/api/demo-labels'),
  scanDemo: (key) => request(`/api/scan/demo/${encodeURIComponent(key)}`, { method: 'POST' }),
  getScan: (id) => request(`/api/scan/${id}`),
  listScans: (limit = 50) => request(`/api/scans?limit=${limit}`),
  explain: (scan_id, language, eli12, member) =>
    request('/api/scan/explain', { method: 'POST', body: { scan_id, language, eli12, member } }),

  alternatives: (scanId, member) => request(`/api/alternatives/${scanId}${q(member)}`),
  feedback: (payload) => request('/api/alternatives/feedback', { method: 'POST', body: payload }),

  compare: (scan_ids, member) => request('/api/compare', { method: 'POST', body: { scan_ids, member } }),

  log: (scan_id, member, servings) => request('/api/log', { method: 'POST', body: { scan_id, member, servings } }),
  tracker: (days = 7) => request(`/api/tracker?days=${days}`),
  report: (language = 'en', refresh = false) => request(`/api/report?language=${language}${refresh ? '&refresh=true' : ''}`),
}
