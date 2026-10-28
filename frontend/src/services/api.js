const API = import.meta.env.VITE_API_URL || ''

async function jsonFetch(url, options = {}) {
  const res = await fetch(`${API}${url}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail || body.error || `HTTP ${res.status}`)
  return body
}

export const getCapabilities = () => jsonFetch('/api/capabilities')
export const getDefaultAoi = () => jsonFetch('/api/aoi/default')
export const submitJob = (payload) => jsonFetch('/api/jobs', { method: 'POST', body: JSON.stringify(payload) })
export const getJob = (id) => jsonFetch(`/api/jobs/${id}`)
