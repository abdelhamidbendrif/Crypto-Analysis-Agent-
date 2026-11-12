import type { Mode, Session, SessionSummary, SourceData } from './types'

const base = import.meta.env.VITE_API_URL || ''
let memoryOwner = ''

function workspaceId(): string {
  try {
    const saved = sessionStorage.getItem('crypto-workspace')
    if (saved) return saved
    const owner = crypto.randomUUID()
    sessionStorage.setItem('crypto-workspace', owner)
    return owner
  } catch {
    memoryOwner ||= crypto.randomUUID()
    return memoryOwner
  }
}

export class ApiError extends Error {
  constructor(message: string, public status = 0, public contextReset = false) { super(message) }
}

async function request<T>(path: string, init: RequestInit = {}, blob = false): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 150_000)
  try {
    const response = await fetch(`${base}/api${path}`, {
      ...init, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', 'X-Workspace-ID': workspaceId(), ...init.headers },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      const detail = payload.detail
      const message = typeof detail === 'string' ? detail : detail?.message
      throw new ApiError(message || 'The request was not accepted. Check your input and try again.', response.status, !!detail?.context_reset)
    }
    return (blob ? await response.blob() : await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Cannot reach the backend or the request timed out. Refresh the conversation before retrying; an in-flight request may still finish.')
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  sessions: () => request<SessionSummary[]>('/sessions'),
  create: (mode: Mode) => request<Session>('/sessions', { method: 'POST', body: JSON.stringify({ mode }) }),
  get: (id: string) => request<Session>(`/sessions/${id}`),
  preview: () => request<SourceData>('/demo/preview'),
  research: (id: string, action: string, body: object) => request<Session>(`/sessions/${id}/${action}`, { method: 'POST', body: JSON.stringify(body) }),
  report: (id: string, turn: string) => request<Blob>(`/sessions/${id}/reports/${turn}`, {}, true),
}

export async function downloadReport(session: Session, turn: string): Promise<void> {
  const blob = await api.report(session.id, turn)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'crypto-research-report.md'
  link.click()
  URL.revokeObjectURL(url)
}
