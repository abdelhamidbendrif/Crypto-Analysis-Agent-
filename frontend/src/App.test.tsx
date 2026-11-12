import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api, ApiError, downloadReport } from './api'
import { formatPrice, safeUrl } from './components'
import type { Session, Snapshot, SourceData, Turn } from './types'

vi.mock('./api', async importOriginal => {
  const original = await importOriginal<typeof import('./api')>()
  return { ...original, downloadReport: vi.fn(), api: { sessions: vi.fn(), create: vi.fn(), get: vi.fn(), preview: vi.fn(), research: vi.fn() } }
})

const snapshot: Snapshot = { symbol: 'BTC', last: '75000.0123', change: '1.25', low: '73000', high: '76000', quote_currency: 'USD (fictional sample)', source_timestamp: '2026-01-01T12:00:00Z', timezone: 'UTC (sample)', period: 'Sample period', change_baseline: 'Sample baseline', exchange: 'Sample exchange', provider: 'Demo fixtures', fetched_at: '2026-01-01T12:00:00Z' }
const data: SourceData = { snapshots: [snapshot, { ...snapshot, symbol: 'ETH', last: '2500' }], articles: [{ title: 'Sample Bitcoin headline', source: 'Sample publisher', url: 'https://example.com/demo', publishedAt: '2026-01-01T12:00:00Z', query: 'bitcoin', provider: 'Demo', fetched_at: null }], coins: [], evidence: [] }
const empty: SourceData = { snapshots: [], articles: [], coins: [], evidence: [] }
const initial: Session = { id: 'session-demo', mode: 'demo', title: 'New conversation', turn_count: 0, created_at: '2026-01-01', updated_at: '2026-01-01', turns: [], latest: empty, busy: false }
const turn: Turn = { id: 'turn-1', query: 'BTC snapshot', reply: '## Summary\nBTC source-backed result', created_at: '2026-01-01', elapsed: .5, evidence: [{ tool: 'crypto_data_tool', args: { symbol: 'BTC' }, data: { provider: 'Demo fixtures' }, failed: false }] }
const answered: Session = { ...initial, title: 'BTC snapshot', turn_count: 1, turns: [turn], latest: data }
const nav = (name: string) => within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name })
async function ready() { await waitFor(() => expect(screen.getByText('Backend connected')).toBeInTheDocument()) }

beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear(); localStorage.clear()
  vi.mocked(api.sessions).mockResolvedValue([])
  vi.mocked(api.create).mockImplementation(async mode => ({ ...initial, id: `session-${mode}`, mode }))
  vi.mocked(api.preview).mockResolvedValue(data)
  vi.mocked(api.research).mockResolvedValue(answered)
  vi.mocked(api.get).mockResolvedValue(answered)
  vi.mocked(downloadReport).mockResolvedValue()
})

describe('Research workspace', () => {
  it('loads a labelled demo preview without making agent requests', async () => {
    render(<App />); await ready()
    expect(screen.getByText(/All sample prices/)).toBeInTheDocument()
    expect(screen.getByText('75,000.0123')).toBeInTheDocument()
    expect(screen.getByText('Sample Bitcoin headline').closest('a')).toHaveAttribute('href', 'https://example.com/demo')
    expect(api.research).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Export report' })).toBeDisabled()
  })

  it('sends chat to the backend and retains the session for follow-up questions', async () => {
    render(<App />); await ready()
    fireEvent.change(screen.getByLabelText('Ask the analyst'), { target: { value: 'BTC snapshot' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
    await screen.findByText('BTC source-backed result')
    expect(api.research).toHaveBeenLastCalledWith('session-demo', 'chat', { message: 'BTC snapshot' })
    fireEvent.change(screen.getByLabelText('Ask the analyst'), { target: { value: 'News about the same cryptocurrency' } })
    fireEvent.keyDown(screen.getByLabelText('Ask the analyst'), { key: 'Enter' })
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-demo', 'chat', { message: 'News about the same cryptocurrency' }))
    expect(screen.getByText('Sources & tools')).toBeInTheDocument()
  })

  it('shows loading and prevents duplicate sends while research is pending', async () => {
    let finish!: (session: Session) => void
    vi.mocked(api.research).mockReturnValue(new Promise(resolve => { finish = resolve }))
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'BTC snapshot' }))
    expect(screen.getByRole('status')).toHaveTextContent('Opening the sample scenario')
    expect(screen.getByLabelText('Ask the analyst')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'New conversation' })).toBeDisabled()
    await act(async () => finish(answered))
    expect(screen.getByLabelText('Ask the analyst')).toBeEnabled()
  })

  it('switches themes without creating or losing conversations', async () => {
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'BTC snapshot' }))
    await screen.findByText('BTC source-backed result')
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('crypto-theme')).toBe('dark')
    expect(screen.getByText('BTC source-backed result')).toBeInTheDocument()
    expect(api.create).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('switches to live mode with an isolated session and no demo quotes', async () => {
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Live APIs' }))
    await waitFor(() => expect(api.create).toHaveBeenLastCalledWith('live'))
    await waitFor(() => expect(screen.getByLabelText('Ask the analyst')).toBeEnabled())
    expect(screen.queryByText('75,000.0123')).not.toBeInTheDocument()
    expect(screen.queryByText('Sample Bitcoin headline')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'BTC snapshot' }))
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-live', 'chat', expect.anything()))
  })

  it('uses the comparison endpoint and disables identical asset requests', async () => {
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('tab', { name: 'Comparison' }))
    const controls = within(screen.getByRole('group', { name: 'Asset comparison' }))
    fireEvent.click(controls.getByRole('button', { name: 'Compare assets' }))
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-demo', 'compare', { symbols: ['BTC', 'ETH'] }))
    await waitFor(() => expect(controls.getByLabelText('Second asset')).toBeEnabled())
    fireEvent.change(controls.getByLabelText('Second asset'), { target: { value: 'BTC' } })
    expect(controls.getByRole('button', { name: 'Compare assets' })).toBeDisabled()
  })

  it('supports arrow-key navigation between context tabs', async () => {
    render(<App />); await ready()
    fireEvent.keyDown(screen.getByRole('tab', { name: 'News' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Comparison' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Comparison' })).toHaveFocus()
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Comparison' }), { key: 'Home' })
    expect(screen.getByRole('tab', { name: 'News' })).toHaveAttribute('aria-selected', 'true')
  })

  it('searches news through the endpoint and exports the original report', async () => {
    render(<App />); await ready()
    fireEvent.click(nav('News watch'))
    fireEvent.change(screen.getByLabelText('News topic'), { target: { value: 'Ethereum' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search news' }))
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-demo', 'news', { query: 'Ethereum', max_items: 3 }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Export report' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Export report' }))
    await waitFor(() => expect(downloadReport).toHaveBeenCalledWith(answered, 'turn-1'))
  })

  it('restores previous conversations and creates a new independent one', async () => {
    vi.mocked(api.sessions).mockResolvedValue([{ ...answered, id: 'old-session' }])
    vi.mocked(api.get).mockResolvedValue({ ...answered, id: 'old-session' })
    render(<App />); await ready()
    fireEvent.click(nav('Conversations'))
    fireEvent.click(screen.getByRole('button', { name: /BTC snapshot.*1 turn/ }))
    await screen.findByText('BTC source-backed result')
    expect(api.get).toHaveBeenCalledWith('old-session')
    fireEvent.click(screen.getByRole('button', { name: 'New conversation' }))
    await waitFor(() => expect(api.create).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByText('BTC source-backed result')).not.toBeInTheDocument())
  })

  it('recovers the reset conversation after backend failure and displays a friendly error', async () => {
    vi.mocked(api.research).mockRejectedValue(new ApiError('Conversation context was reset; please retry.', 502, true))
    vi.mocked(api.get).mockResolvedValue(initial)
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'BTC snapshot' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Conversation context was reset')
    expect(api.get).toHaveBeenCalledWith('session-demo')
    await waitFor(() => expect(screen.getByLabelText('Ask the analyst')).toBeEnabled())
  })

  it('supports closing mobile navigation with Escape', async () => {
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    expect(screen.getByRole('dialog', { name: 'Workspace navigation' })).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('browses returned assets and fetches a selected symbol', async () => {
    vi.mocked(api.research).mockResolvedValue({ ...answered, latest: { ...empty, coins: [{ symbol: 'BTC', name: 'Bitcoin' }] } })
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Browse assets' }))
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-demo', 'assets', {}))
    fireEvent.click(await screen.findByRole('button', { name: 'BTC · Bitcoin' }))
    await waitFor(() => expect(api.research).toHaveBeenLastCalledWith('session-demo', 'market', { symbols: ['BTC'] }))
  })

  it('exports the selected report rather than a different response', async () => {
    const secondTurn = { ...turn, id: 'turn-2', query: 'ETH snapshot', reply: 'Ethereum source report' }
    vi.mocked(api.research).mockResolvedValue({ ...answered, turns: [turn, secondTurn], turn_count: 2 })
    render(<App />); await ready()
    fireEvent.click(screen.getByRole('button', { name: 'BTC snapshot' }))
    await screen.findByText('Ethereum source report')
    fireEvent.click(nav('Reports'))
    fireEvent.change(screen.getByLabelText('Choose a report'), { target: { value: 'turn-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Download Markdown' }))
    await waitFor(() => expect(downloadReport).toHaveBeenCalledWith(expect.anything(), 'turn-1'))
  })
})

describe('Source formatting', () => {
  it('retains exact price precision without adding currency', () => {
    expect(formatPrice('75000.01234567')).toBe('75,000.01234567')
    expect(formatPrice('0.00012345')).toBe('0.00012345')
    expect(formatPrice('123456789')).toBe('123,456,789')
  })
  it('rejects unsafe or credential-bearing source links', () => {
    expect(safeUrl('javascript:alert(1)')).toBeUndefined()
    expect(safeUrl('https://user:secret@example.com')).toBeUndefined()
    expect(safeUrl('https://example.com/story')).toBe('https://example.com/story')
  })
})
