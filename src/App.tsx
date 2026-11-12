import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { ArrowDownToLine, ArrowRight, ArrowUpRight, Check, CircleHelp, Columns2, FileText, LayoutDashboard, LoaderCircle, Menu, MessageSquare, Moon, Newspaper, Paperclip, Plus, RefreshCw, Search, Send, ShieldCheck, Sun, User, X } from 'lucide-react'
import { api, ApiError, downloadReport } from './api'
import { BrandLogo, Comparison, EmptyState, ErrorBanner, IconButton, NewsList, ReportView, SnapshotCards, StructuredReply } from './components'
import type { Mode, Session, SessionSummary, SourceData, View } from './types'

const emptyData: SourceData = { snapshots: [], articles: [], coins: [], evidence: [] }
const navigation = [
  { id: 'desk', label: 'Research desk', icon: LayoutDashboard },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
  { id: 'compare', label: 'Compare assets', icon: Columns2 },
  { id: 'news', label: 'News watch', icon: Newspaper },
  { id: 'reports', label: 'Reports', icon: FileText },
] as const
const starters = [
  { label: 'BTC snapshot', icon: Search, query: 'Give me current market data for BTC.' },
  { label: 'ETH snapshot', icon: Search, query: 'Give me current market data for ETH.' },
  { label: 'Compare BTC / ETH', icon: Columns2, query: 'Compare current market data for BTC and ETH. Preserve source units and timestamps.' },
  { label: 'Latest BTC news', icon: Newspaper, query: 'Give me three recent news articles about Bitcoin.' },
]

function readStorage(key: string): string | null { try { return sessionStorage.getItem(key) } catch { return null } }
function rememberSession(session: Session) { try { sessionStorage.setItem(`crypto-active-${session.mode}`, session.id) } catch { /* Storage is optional. */ } }
function formatTurnTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function App() {
  const [mode, setMode] = useState<Mode>(() => readStorage('crypto-mode') === 'live' ? 'live' : 'demo')
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem('crypto-theme') === 'dark' ? 'dark' : 'light' } catch { return 'light' } })
  const [view, setView] = useState<View>('desk')
  const [session, setSession] = useState<Session | null>(null)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [preview, setPreview] = useState<SourceData>(emptyData)
  const [busy, setBusy] = useState(true)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const [draft, setDraft] = useState('')
  const [drawer, setDrawer] = useState(false)
  const [tab, setTab] = useState<'news' | 'compare'>('news')
  const [first, setFirst] = useState('BTC')
  const [second, setSecond] = useState('ETH')
  const [topic, setTopic] = useState('bitcoin')
  const [count, setCount] = useState(3)
  const [reportId, setReportId] = useState('')
  const [retry, setRetry] = useState(0)
  const transcript = useRef<HTMLDivElement>(null)
  const sidebar = useRef<HTMLElement>(null)
  const mobileMenu = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('crypto-theme', theme) } catch { /* Keep the active theme without persistence. */ }
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#1C1D1B' : '#F7F5EF')
  }, [theme])

  useEffect(() => {
    let stopped = false
    setBusy(true); setError(''); setSession(null); setPending(''); setPreview(emptyData)
    async function connect() {
      try {
        const list = await api.sessions()
        const stored = readStorage(`crypto-active-${mode}`)
        let current: Session
        if (stored && list.some(item => item.id === stored && item.mode === mode)) current = await api.get(stored)
        else current = await api.create(mode)
        const samples = mode === 'demo' ? await api.preview() : emptyData
        if (stopped) return
        setSession(current); setSessions([current, ...list.filter(item => item.id !== current.id)])
        setPreview(samples); setConnected(true); rememberSession(current)
      } catch (cause) {
        if (!stopped) { setConnected(false); setError(cause instanceof Error ? cause.message : 'Could not connect to the backend.') }
      } finally { if (!stopped) setBusy(false) }
    }
    void connect()
    return () => { stopped = true }
  }, [mode, retry])

  useEffect(() => {
    const container = transcript.current
    if (!container) return
    const turnsEls = container.querySelectorAll<HTMLElement>('.turn')
    const latestEl = turnsEls[turnsEls.length - 1]
    if (latestEl) {
      const targetTop = Math.max(0, latestEl.offsetTop - 14)
      container.scrollTo?.({ top: targetTop, behavior: 'instant' })
    } else {
      container.scrollTo?.({ top: container.scrollHeight, behavior: 'instant' })
    }
  }, [session?.turns.length, pending])

  useEffect(() => {
    if (!drawer) return
    const priorOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusable = () => Array.from(sidebar.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || [])
    focusable()[0]?.focus()
    const trap = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setDrawer(false); mobileMenu.current?.focus() }
      if (event.key === 'Tab') {
        const items = focusable(), head = items[0], tail = items.at(-1)
        if (event.shiftKey && document.activeElement === head) { event.preventDefault(); tail?.focus() }
        else if (!event.shiftKey && document.activeElement === tail) { event.preventDefault(); head?.focus() }
      }
    }
    document.addEventListener('keydown', trap)
    return () => { document.body.style.overflow = priorOverflow; document.removeEventListener('keydown', trap) }
  }, [drawer])

  const commitSession = (value: Session) => {
    setSession(value); rememberSession(value)
    setSessions(previous => [value, ...previous.filter(item => item.id !== value.id)])
  }
  const go = (value: View) => { setView(value); setDrawer(false) }
  const researchDisabled = busy || !session || session.busy
  const isPreview = mode === 'demo' && !!session && !session.turns.length
  const data = isPreview ? preview : session?.latest || emptyData
  const showPreviewNews = mode === 'demo' && !data.articles.length && preview.articles.length > 0
  const railArticles = showPreviewNews ? preview.articles : data.articles
  const turns = session?.turns || []
  const selectedReport = turns.find(turn => turn.id === reportId) || turns.at(-1)
  const options = mode === 'demo' ? ['BTC', 'ETH'] : [...new Set(['BTC', 'ETH', 'LTC', 'BNB', ...data.coins.map(coin => coin.symbol)])]
  const firstAsset = options.includes(first) ? first : 'BTC'
  const secondAsset = options.includes(second) ? second : 'ETH'

  async function refresh() {
    if (!session) { setRetry(value => value + 1); return }
    setBusy(true)
    try { commitSession(await api.get(session.id)); setError(''); setConnected(true) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not refresh the conversation.') }
    finally { setBusy(false) }
  }

  async function newConversation() {
    setBusy(true); setError(''); setPending(''); setDraft('')
    try { commitSession(await api.create(mode)); go('desk') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create a conversation.') }
    finally { setBusy(false) }
  }

  async function restore(id: string) {
    setBusy(true); setError('')
    try { commitSession(await api.get(id)); go('desk'); setDraft('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not restore this conversation.') }
    finally { setBusy(false) }
  }

  async function execute(action: string, body: object, query: string) {
    if (!session || researchDisabled) return
    setBusy(true); setError(''); setPending(query)
    try { commitSession(await api.research(session.id, action, body)); setDraft('') }
    catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Research failed. Please retry.')
      if (cause instanceof ApiError && (cause.contextReset || cause.status === 0 || cause.status === 409)) {
        try { commitSession(await api.get(session.id)) } catch { /* Retain the failure message and allow a manual refresh. */ }
      }
    } finally { setBusy(false); setPending('') }
  }

  async function exportReport(id = selectedReport?.id) {
    if (!session || !id) return
    setBusy(true)
    try { await downloadReport(session, id) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Report download failed.') }
    finally { setBusy(false) }
  }

  const chat = (query: string) => execute('chat', { message: query }, query)
  const market = (symbol: string) => execute('market', { symbols: [symbol] }, `Get a market snapshot for ${symbol}.`)
  const fetchComparison = () => execute('compare', { symbols: [firstAsset, secondAsset] }, `Compare current market data for ${firstAsset} and ${secondAsset}.`)
  const fetchNews = () => execute('news', { query: topic.trim(), max_items: mode === 'demo' ? 3 : count }, `Find ${mode === 'demo' ? 3 : count} recent articles about ${topic.trim()}.`)

  function handleTabKey(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'Home' ? 'news' : event.key === 'End' ? 'compare' : tab === 'news' ? 'compare' : 'news'
    setTab(next)
    document.getElementById(`${next}-tab`)?.focus()
  }

  const comparisonControls = <div className="comparison-controls" role="group" aria-label="Asset comparison"><div className="grid grid-cols-2 gap-3">
    <label>First asset<select value={firstAsset} onChange={event => setFirst(event.target.value)} disabled={busy}>{options.map(symbol => <option key={symbol}>{symbol}</option>)}</select></label>
    <label>Second asset<select value={secondAsset} onChange={event => setSecond(event.target.value)} disabled={busy}>{options.map(symbol => <option key={symbol}>{symbol}</option>)}</select></label>
  </div><button className="button primary w-full mt-3" onClick={() => void fetchComparison()} disabled={researchDisabled || firstAsset === secondAsset}><Columns2 size={14} />Compare assets</button>
    {firstAsset === secondAsset && <p className="tiny muted mt-2">Choose two different assets.</p>}</div>

  const hasConversation = turns.length > 0 || !!pending

  const composerDock = (
    <div className={`composer-dock ${hasConversation ? 'is-pinned' : 'is-centered'}`}>
      {!hasConversation && (
        <div className="suggestions" aria-label="Suggested questions">
          {starters.map(({ label, icon: Icon, query }) => (
            <button key={label} onClick={() => void chat(query)} disabled={researchDisabled}>
              <Icon size={12} />{label}
            </button>
          ))}
        </div>
      )}
      <form className="composer" onSubmit={event => { event.preventDefault(); if (draft.trim()) void chat(draft.trim()) }}>
        <label className="sr-only" htmlFor="question">Ask the analyst</label>
        <textarea
          id="question"
          rows={2}
          maxLength={2000}
          value={draft}
          disabled={researchDisabled}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              if (draft.trim() && !researchDisabled) void chat(draft.trim())
            }
          }}
          placeholder='Ask a research question… (e.g., "Compare BTC and ETH", "Latest BTC news")'
        />
        <div className="composer-toolbar">
          <div className="composer-tools">
            <button
              type="button"
              className="composer-attach"
              aria-label="Insert sample question"
              title="Insert sample question"
              disabled={researchDisabled}
              onClick={() => setDraft('Compare BTC and ETH market snapshot, key trends, and recent news.')}
            >
              <Paperclip size={15} />
            </button>
            <span className="composer-mode-text">
              {mode === 'demo' ? 'Demo mode · Fictional quotes' : 'Source-aware · Live APIs'}
            </span>
          </div>
          <button aria-label="Send question" className="send-button" disabled={researchDisabled || !draft.trim()} type="submit">
            <Send size={15} />
          </button>
        </div>
      </form>
      <div className="composer-footnote">
        <span>Enter to send · Shift + Enter for new line</span>
        <span>{mode === 'demo' ? 'Sources attached to every answer' : 'Source values stay visible · missing context stays unknown'}</span>
      </div>
    </div>
  )

  const researchStage = (
    <section className={`chat-stage ${hasConversation ? 'has-turns' : 'is-empty'}`} aria-label="AI Analyst conversation">
      {!hasConversation ? (
        <div className="chat-hero-center">
          <div className="welcome">
            <div className="welcome-orb" aria-hidden="true">
              <span className="welcome-orb-inner"><BrandLogo size={24} /></span>
            </div>
            <h2>How can I help your research today?</h2>
            <p>Ask for live crypto quotes, compare assets side by side, or verify headlines with attached sources.</p>
          </div>
          {composerDock}
        </div>
      ) : (
        <>
          <div className="transcript" ref={transcript} aria-label="Conversation messages" aria-busy={!!pending}>
            <div className="transcript-inner">
              {turns.map(turn => {
                const time = formatTurnTime(turn.created_at)
                return (
                  <div className="turn" key={turn.id}>
                    <div className="user-message">
                      <span className="user-avatar" aria-hidden="true"><User size={13} /></span>
                      <p>{turn.query}</p>
                      {time && <span className="turn-time">{time}</span>}
                    </div>
                    <StructuredReply
                      turn={turn}
                      mode={mode}
                      onExport={() => void exportReport(turn.id)}
                      exportDisabled={busy}
                    />
                  </div>
                )
              })}
              {pending && (
                <div className="turn">
                  <div className="user-message">
                    <span className="user-avatar" aria-hidden="true"><User size={13} /></span>
                    <p>{pending}</p>
                  </div>
                  <div className="research-loading" role="status">
                    <LoaderCircle size={17} className="spin" />
                    <div>
                      <strong>{mode === 'demo' ? 'Opening the sample scenario' : 'Researching with your agent'}</strong>
                      <p>{mode === 'demo' ? 'Fictional data · no external calls' : 'Selecting tools, fetching sources and preparing the report…'}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          {composerDock}
        </>
      )}
    </section>
  )

  const currentNav = navigation.find(item => item.id === view)
  const topTitle = view === 'desk' ? (hasConversation && session?.title ? session.title : 'Crypto Research AI') : currentNav?.label

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to workspace</a>
    {drawer && <button className="drawer-backdrop" aria-label="Close navigation overlay" onClick={() => setDrawer(false)} />}
    <aside className={`sidebar ${drawer ? 'is-open' : ''}`} ref={sidebar} role={drawer ? 'dialog' : undefined} aria-modal={drawer || undefined} aria-label="Workspace navigation">
      <div className="brand">
        <span className="brand-icon"><BrandLogo size={18} /></span>
        <div>Crypto Research AI<span>AI market research</span></div>
        <button className="mobile-close icon-button" aria-label="Close navigation" onClick={() => setDrawer(false)}><X size={18} /></button>
      </div>
      <button className="button new-conversation" onClick={() => void newConversation()} disabled={busy}><Plus size={15} />New conversation</button>
      <nav aria-label="Main navigation">
        {navigation.map(({ id, label, icon: Icon }) => <button className={`nav-item ${view === id ? 'active' : ''}`} aria-current={view === id ? 'page' : undefined} key={id} onClick={() => go(id)}>
          <Icon size={16} strokeWidth={1.8} />{label}
        </button>)}
      </nav>
      {sessions.some(item => item.mode === mode && item.turn_count > 0) && (
        <div className="sidebar-recent" aria-label="Recent sessions">
          <div className="sidebar-recent-label">Recent</div>
          {sessions.filter(item => item.mode === mode && item.turn_count > 0).slice(0, 4).map(item => (
            <button
              key={item.id}
              type="button"
              className={`recent-item ${item.id === session?.id ? 'is-current' : ''}`}
              disabled={busy}
              onClick={() => void restore(item.id)}
              title={item.title}
            >
              <span>{item.title}</span>
            </button>
          ))}
        </div>
      )}
      <div className="sidebar-bottom">
        <div className="flex items-center justify-between">
          <h2>Data mode</h2>
          <CircleHelp size={13} className="muted" aria-hidden="true" />
        </div>
        <div className="mode-switch" role="group" aria-label="Data mode">
          {(['demo', 'live'] as Mode[]).map(value => <button key={value} aria-pressed={mode === value} disabled={busy} onClick={() => { if (value === mode) return; setMode(value); try { sessionStorage.setItem('crypto-mode', value) } catch { /* Optional persistence. */ } }}>
            {value === 'demo' ? 'Demo' : 'Live APIs'}
          </button>)}
        </div>
        <p className="mode-description">
          <span className={`status-dot ${mode === 'demo' ? 'sample-dot' : ''}`} />
          {mode === 'demo' ? 'Fictional samples · no API calls' : 'Real requests · uses API quota'}
        </p>
        <div className="workspace-identity">
          <span className="workspace-avatar" aria-hidden="true"><BrandLogo size={15} /></span>
          <div>
            <strong>Crypto Research</strong>
            <span>Source-aware workspace</span>
          </div>
        </div>
      </div>
    </aside>

    <main className="main-workspace" id="main">
      <header className="topbar">
        <div className="topbar-left">
          <button className="mobile-menu icon-button" ref={mobileMenu} aria-label="Open navigation" onClick={() => setDrawer(true)}><Menu size={18} /></button>
          <h1 className="topbar-title">{topTitle}</h1>
          <span className="topbar-mode-tag">{mode === 'demo' ? 'DEMO' : 'LIVE APIs'}</span>
        </div>
        <div className="header-actions">
          <span className="connection-label">
            <span className={`status-dot ${!connected ? 'offline-dot' : ''}`} />
            {connected ? 'Backend connected' : busy ? 'Connecting' : 'Offline'}
          </span>
          <button
            className="theme-toggle"
            type="button"
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            onClick={() => setTheme(value => value === 'light' ? 'dark' : 'light')}
          >
            <span className={`theme-toggle-option ${theme === 'light' ? 'is-active' : ''}`} aria-hidden="true"><Sun size={14} /></span>
            <span className={`theme-toggle-option ${theme === 'dark' ? 'is-active' : ''}`} aria-hidden="true"><Moon size={14} /></span>
          </button>
          <button className="button export-button" onClick={() => void exportReport()} disabled={busy || !selectedReport}>
            <ArrowDownToLine size={14} /><span>Export report</span>
          </button>
        </div>
      </header>

      <div className="mode-strip">
        <p>{mode === 'demo' ? 'All sample prices, dates and headlines are fictional. Switch to Live APIs to use the real agent.' : 'Source data is fetched when you ask. Units, periods and timezones are shown only when provided.'}</p>
        {mode === 'demo' && <span className="banner-right">No API keys needed <Check size={12} /></span>}
      </div>

      {error && <div className="workspace-alerts"><ErrorBanner message={error} onDismiss={() => setError('')} onRefresh={() => void refresh()} /></div>}
      {busy && pending && view !== 'desk' && <div className="workspace-alerts"><div className="research-loading" role="status"><LoaderCircle size={17} className="spin" /><div><strong>Researching your request…</strong><p>{mode === 'demo' ? 'Opening fictional samples' : 'Your agent is selecting tools and checking sources.'}</p></div></div></div>}
      {session?.busy && !busy && <div className="workspace-alerts"><div className="error-banner" role="status"><LoaderCircle size={17} /><div><strong>A request is still running on the backend.</strong><p>Refresh the conversation to retrieve its result before asking again.</p><button onClick={() => void refresh()}>Refresh conversation</button></div></div></div>}

      {view === 'desk' && (
        <div className="desk-studio">
          <div className="desk-main">
            <SnapshotCards data={data} disabled={researchDisabled} onFetch={symbol => void market(symbol)} onAssets={() => void execute('assets', {}, 'Show available cryptocurrency symbols.')} preview={isPreview} />
            {!!session?.latest.coins.length && (
              <details className="rail-assets" open>
                <summary>Available assets · {session.latest.coins.length} returned</summary>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {session.latest.coins.map(coin => (
                    <button className="button compact" disabled={researchDisabled} key={coin.symbol} onClick={() => void market(coin.symbol)}>
                      {coin.symbol}{coin.name ? ` · ${coin.name}` : ''}<ArrowUpRight size={11} />
                    </button>
                  ))}
                </div>
              </details>
            )}
            {researchStage}
          </div>
          <aside className="intel-rail" aria-label="Research context">
            <div className="context-tabs" role="tablist" aria-label="Research context">
              <button role="tab" id="news-tab" tabIndex={tab === 'news' ? 0 : -1} aria-selected={tab === 'news'} aria-controls="news-panel" onKeyDown={handleTabKey} onClick={() => setTab('news')}><Newspaper size={14} />News</button>
              <button role="tab" id="compare-tab" tabIndex={tab === 'compare' ? 0 : -1} aria-selected={tab === 'compare'} aria-controls="compare-panel" onKeyDown={handleTabKey} onClick={() => setTab('compare')}><Columns2 size={14} />Comparison</button>
            </div>
            {tab === 'news' ? (
              <section role="tabpanel" id="news-panel" aria-labelledby="news-tab" className="context-content">
                <div className="flex items-center justify-between gap-2">
                  <h2>Latest Crypto News</h2>
                  <IconButton label="Refresh news" disabled={researchDisabled} onClick={() => void fetchNews()}>
                    <RefreshCw size={13} />
                  </IconButton>
                </div>
                <NewsList articles={railArticles} preview={isPreview || showPreviewNews} />
                <button className="text-button mt-3" onClick={() => go('news')}>View more news <ArrowRight size={13} /></button>
                <div className="context-note"><CircleHelp size={13} className="shrink-0 mt-0.5" aria-hidden="true" /><span>A headline alone does not establish why a price moved.</span></div>
              </section>
            ) : (
              <section role="tabpanel" id="compare-panel" aria-labelledby="compare-tab" className="context-content">
                <h2>Side by side</h2>
                <p className="tiny muted mt-1 mb-3">Compare reported snapshots and provenance.</p>
                {comparisonControls}
                <Comparison snapshots={data.snapshots} compact />
              </section>
            )}
          </aside>
        </div>
      )}

      {view !== 'desk' && (
        <div className="standalone-scroll">
          <div className="standalone-stage">
            {view === 'compare' && <section className="panel standalone-panel"><div className="panel-heading"><div><h2>Compare assets</h2><p>Fetch source data for two assets. Timestamps may differ.</p></div><Columns2 size={18} className="muted" /></div><div className="standalone-content"><div className="max-w-lg mb-5">{comparisonControls}</div><Comparison snapshots={session?.latest.snapshots || []} /></div></section>}
            {view === 'news' && <section className="panel standalone-panel"><div className="panel-heading"><div><h2>News watch</h2><p>Search for headlines, then inspect the original source.</p></div><Newspaper size={18} className="muted" /></div><div className="standalone-content"><form className="news-search" onSubmit={event => { event.preventDefault(); void fetchNews() }}><label>News topic<input maxLength={150} value={topic} onChange={event => setTopic(event.target.value)} placeholder="Bitcoin, Ethereum…" disabled={busy} /></label><label>Articles<select value={mode === 'demo' ? 3 : count} onChange={event => setCount(Number(event.target.value))} disabled={busy || mode === 'demo'}>{[3, 5, 10].map(value => <option key={value}>{value}</option>)}</select></label><button className="button primary" disabled={researchDisabled || !topic.trim()} type="submit"><Search size={14} />Search news</button></form>{busy && pending && <p role="status" className="small muted mb-3">Searching with the analyst…</p>}<NewsList articles={data.articles} preview={isPreview} max={10} /></div></section>}
            {view === 'conversations' && <section className="panel standalone-panel"><div className="panel-heading"><div><h2>Conversations</h2><p>{mode === 'demo' ? 'Demo' : 'Live API'} sessions in this browser workspace. Local backend memory expires after 4 hours of inactivity.</p></div><button className="button" disabled={busy} onClick={() => void newConversation()}><Plus size={14} />New conversation</button></div><div className="standalone-content">
              {!sessions.filter(item => item.mode === mode && item.turn_count).length && <EmptyState icon={<MessageSquare size={22} />} title="Your research starts here" text="Ask a question from the Research Desk. You can come back to continue it here." />}
              {sessions.filter(item => item.mode === mode && item.turn_count).map(item => <button className="conversation-row" disabled={busy} key={item.id} onClick={() => void restore(item.id)}><span className="subtle-icon"><MessageSquare size={16} /></span><span><strong>{item.title}</strong><small>{item.turn_count} turn(s) · {item.mode === 'demo' ? 'Fictional demo' : 'Live APIs'}{item.id === session?.id ? ' · Current' : ''}</small></span><ArrowRight size={16} /></button>)}
            </div></section>}
            {view === 'reports' && <>{!selectedReport ? <section className="panel"><EmptyState icon={<FileText size={22} />} title="Research worth keeping" text="Reports appear after the analyst answers. Restore another conversation to access its reports." /></section> : <><label className="report-selector">Choose a report<select value={selectedReport.id} onChange={event => setReportId(event.target.value)}>{turns.map((turn, index) => <option value={turn.id} key={turn.id}>Response {index + 1} · {turn.query.slice(0, 65)}</option>)}</select></label><ReportView turn={selectedReport} onDownload={() => void exportReport(selectedReport.id)} disabled={busy} /></>}</>}
            <footer className="workspace-footer"><span><ShieldCheck size={12} />Source-aware research</span><span>Educational use · Not investment advice</span></footer>
          </div>
        </div>
      )}
    </main>
  </div>
}
