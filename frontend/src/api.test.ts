import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

beforeEach(() => { sessionStorage.clear(); vi.stubGlobal('fetch', vi.fn()) })
afterEach(() => { vi.unstubAllGlobals() })

it('sends JSON and a stable workspace identifier, with no credentials in URLs', async () => {
  vi.mocked(fetch).mockImplementation(async () => new Response(JSON.stringify({ id: 'one' }), { status: 200 }))
  await api.create('demo')
  await api.sessions()
  const first = vi.mocked(fetch).mock.calls[0]
  const second = vi.mocked(fetch).mock.calls[1]
  expect(first[0]).toBe('/api/sessions')
  expect(first[1]?.body).toBe(JSON.stringify({ mode: 'demo' }))
  const headers = first[1]?.headers as Record<string, string>
  expect(headers['X-Workspace-ID']).toMatch(/^[0-9a-f-]{36}$/i)
  expect((second[1]?.headers as Record<string, string>)['X-Workspace-ID']).toBe(headers['X-Workspace-ID'])
})

it('preserves safe backend error codes and checkpoint-reset information', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ detail: { message: 'Please retry safely', context_reset: true } }), { status: 502 }))
  await expect(api.research('one', 'chat', { message: 'BTC' })).rejects.toMatchObject({ status: 502, contextReset: true, message: 'Please retry safely' })
})

it('explains unknown request state after a network failure', async () => {
  vi.mocked(fetch).mockRejectedValue(new TypeError('Network failure'))
  try { await api.get('one'); throw new Error('Expected network failure') }
  catch (error) {
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
    expect((error as Error).message).toMatch(/Refresh the conversation before retrying/)
  }
})

it('downloads report content as a blob through the protected endpoint', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response('# DEMO report', { headers: { 'Content-Type': 'text/markdown' } }))
  const report = await api.report('one', 'turn-one')
  expect(report.type).toBe('text/markdown')
  expect(report.size).toBeGreaterThan(0)
  expect(await report.text()).toBe('# DEMO report')
  expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/sessions/one/reports/turn-one')
})
