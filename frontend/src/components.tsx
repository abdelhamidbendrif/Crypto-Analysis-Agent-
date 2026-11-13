import { useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowDownToLine, ArrowUpRight, BarChart3, ChevronDown, Database, FileText, Link2, RefreshCw, Search, ShieldCheck, TrendingUp, TriangleAlert } from 'lucide-react'
import type { Article, Evidence, Mode, Snapshot, SourceData, Turn } from './types'
import btcThumb from './assets/images/news_thumb_bitcoin_1794512393923.jpg'
import ethThumb from './assets/images/news_thumb_ethereum_1794512394004.jpg'
import instThumb from './assets/images/news_thumb_institutional_1794512394925.jpg'

const ASSET_NAMES: Record<string, string> = {
  BTC: 'Bitcoin',
  ETH: 'Ethereum',
  LTC: 'Litecoin',
  BNB: 'BNB',
}

export function safeUrl(value: string): string | undefined {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined
  } catch { return undefined }
}

export function formatPrice(value: string): string {
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, (_match, offset: number) => {
    const decimal = value.indexOf('.')
    return decimal < 0 || offset < decimal ? ',' : ''
  })
}

export function IconButton({ label, children, onClick, disabled = false }: {
  label: string; children: ReactNode; onClick: () => void; disabled?: boolean
}) {
  return <button className="icon-button" aria-label={label} title={label} onClick={onClick} disabled={disabled}>{children}</button>
}

export function Markdown({ content }: { content: string }) {
  return <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}
    urlTransform={url => safeUrl(url) || ''}
    components={{
      a: ({ href, children }) => href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}<ArrowUpRight size={12} className="inline" /></a> : <span>{children}</span>,
      img: ({ alt }) => <span>{alt}</span>,
      table: ({ children }) => <div className="table-scroll"><table>{children}</table></div>,
    }}>{content}</ReactMarkdown></div>
}

export function SourceDetails({ evidence, elapsed }: { evidence: Evidence[]; elapsed?: number }) {
  if (!evidence.length) return <p className="tiny muted mt-2">Conversational reply · no tools used for this turn</p>
  const providers = [...new Set(evidence.map(item => item.data.provider).filter(value => typeof value === 'string'))] as string[]
  return <details className="source-details"><summary><Link2 size={13} /> Sources & tools <span className="counter">{evidence.length}</span><ChevronDown size={13} className="ml-auto" /></summary>
    <div className="source-content">
      <div className="flex flex-wrap gap-2">{providers.map(provider => <span className="source-tag" key={provider}>{provider}</span>)}</div>
      {elapsed !== undefined && <p className="tiny muted my-2">Completed in {elapsed.toFixed(1)}s · source results, not private model reasoning</p>}
      {evidence.map((item, index) => <details className="raw-result" key={index}>
        <summary><Database size={12} />{item.tool}<span className={item.failed ? 'negative' : 'muted'}>{item.failed ? 'Failed' : 'Returned'}</span></summary>
        <pre>{JSON.stringify({ arguments: item.args, response: item.data }, null, 2)}</pre>
      </details>)}
    </div>
  </details>
}

export function BrandLogo({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.25" stroke="currentColor" strokeWidth="1.65" opacity="0.35" />
      <path
        d="M12 3.75L18.25 12L12 20.25L5.75 12L12 3.75Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M6.2 12H17.8M12 3.9V20.1"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinecap="round"
        opacity="0.65"
      />
      <circle cx="12" cy="12" r="2.1" fill="currentColor" />
    </svg>
  )
}

export function CoinLogo({ symbol, size = 32 }: { symbol: string; size?: number }) {
  const code = symbol.toUpperCase()
  if (code === 'BTC') {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        <circle cx="16" cy="16" r="16" fill="#F7931A" />
        <path
          d="M21.48 14.12c.29-1.94-1.19-2.98-3.21-3.68l.66-2.63-1.6-.4-.64 2.56c-.42-.1-.85-.2-1.28-.3l.64-2.57-1.6-.4-.66 2.63c-.35-.08-.69-.16-1.02-.24v-.01l-2.21-.55-.43 1.71s1.19.27 1.16.29c.65.16.77.59.75.93l-.75 3.01c.04.01.1.03.17.06-.05-.01-.11-.03-.17-.04l-1.05 4.22c-.08.2-.28.5-.74.38.02.02-1.16-.29-1.16-.29l-.79 1.83 2.08.52c.39.1.77.2 1.14.29l-.66 2.66 1.6.4.66-2.63c.44.12.86.23 1.28.33l-.66 2.62 1.6.4.67-2.66c2.73.52 4.78.31 5.65-2.16.7-1.99-.03-3.13-1.47-3.88 1.05-.24 1.84-.93 2.05-2.36zm-3.67 5.14c-.5 1.99-3.85.91-4.94.64l.88-3.53c1.09.27 4.58.81 4.06 2.89zm.5-5.17c-.45 1.81-3.24.89-4.15.66l.8-3.2c.91.23 3.82.65 3.35 2.54z"
          fill="#FFFFFF"
        />
      </svg>
    )
  }
  if (code === 'ETH') {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        <circle cx="16" cy="16" r="16" fill="#627EEA" />
        <path d="M16.37 5.5v7.76l6.56 2.93L16.37 5.5z" fill="#FFFFFF" fillOpacity="0.65" />
        <path d="M16.37 5.5L9.8 16.19l6.57-2.93V5.5z" fill="#FFFFFF" />
        <path d="M16.37 21.24v5.26l6.57-9.08-6.57 3.82z" fill="#FFFFFF" fillOpacity="0.65" />
        <path d="M16.37 26.5v-5.26L9.8 17.42l6.57 9.08z" fill="#FFFFFF" />
        <path d="M16.37 20.02l6.56-3.83-6.56-2.93v6.76z" fill="#FFFFFF" fillOpacity="0.35" />
        <path d="M9.8 16.19l6.57 3.83v-6.76l-6.57 2.93z" fill="#FFFFFF" fillOpacity="0.85" />
      </svg>
    )
  }
  if (code === 'LTC') {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        <circle cx="16" cy="16" r="16" fill="#345D9D" />
        <path d="M10.4 19.2l1.4-5.2-1.9.7.5-1.9 1.9-.7 1.7-6.1h4.1l-1.3 4.8 2-.7-.5 1.9-2 .7-1.1 4h6.5l-.8 3h-10.6z" fill="#FFFFFF" />
      </svg>
    )
  }
  if (code === 'BNB') {
    return (
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        <circle cx="16" cy="16" r="16" fill="#F3BA2F" />
        <path d="M12.1 14.3L16 10.4l3.9 3.9 2.3-2.3L16 5.8 9.8 12l2.3 2.3zm-6.3 1.7l2.3-2.3 2.3 2.3-2.3 2.3-2.3-2.3zm6.3 1.7L16 21.6l3.9-3.9 2.3 2.3L16 26.2 9.8 20l2.3-2.3zm10-1.7l2.3-2.3 2.3 2.3-2.3 2.3-2.3-2.3zM18.3 16L16 13.7 13.7 16l2.3 2.3L18.3 16z" fill="#FFFFFF" />
      </svg>
    )
  }
  return (
    <span className="coin" style={{ width: size, height: size, fontSize: Math.max(11, Math.round(size * 0.44)) }} aria-hidden="true">
      {code.slice(0, 2)}
    </span>
  )
}

export function SnapshotCards({ data, disabled, onFetch, onAssets, preview }: {
  data: SourceData; disabled: boolean; onFetch: (symbol: string) => void; onAssets: () => void; preview: boolean
}) {
  const snapshots = data.snapshots.slice(0, 2)
  return <section aria-label="Market snapshots" className="market-strip-section">
    <div className="market-strip-header">
      <span className="market-strip-title">{preview ? 'Market snapshot · Fictional sample' : 'Market snapshot · On demand'}</span>
      <button className="text-button" disabled={disabled} onClick={onAssets}><Search size={12} />Browse assets <ArrowUpRight size={12} /></button>
    </div>
    <div className={`market-strip-grid ${snapshots.length === 1 ? 'is-single' : ''}`}>
      {snapshots.length ? snapshots.map(snapshot => <SnapshotCard key={snapshot.symbol} snapshot={snapshot} disabled={disabled} onFetch={onFetch} />)
        : ['BTC', 'ETH'].map(symbol => <article className="market-chip-card" key={symbol}>
          <div className="market-chip-main">
            <div className="snapshot-identity">
              <CoinLogo symbol={symbol} size={26} />
              <div className="min-w-0">
                <strong>{symbol}</strong>
                <span className="snapshot-sub">{ASSET_NAMES[symbol] || symbol}</span>
              </div>
            </div>
            <button className="text-button" disabled={disabled} onClick={() => onFetch(symbol)}>Fetch {symbol} <ArrowUpRight size={12} /></button>
          </div>
        </article>)}
    </div>
  </section>
}

function SnapshotCard({ snapshot: s, disabled, onFetch }: { snapshot: Snapshot; disabled: boolean; onFetch: (symbol: string) => void }) {
  const change = s.change !== null ? Number(s.change) : NaN
  const knownCurrency = s.quote_currency && !/not specified/i.test(s.quote_currency)
  const currencyNote = knownCurrency ? s.quote_currency.replace(' (fictional sample)', ' · sample') : 'Quote unspecified'
  const assetLabel = ASSET_NAMES[s.symbol]
    ? currencyNote ? `${ASSET_NAMES[s.symbol]} · ${currencyNote}` : ASSET_NAMES[s.symbol]
    : currencyNote || 'Market quote'

  return <article className="market-chip-card">
    <div className="market-chip-main">
      <div className="snapshot-identity">
        <CoinLogo symbol={s.symbol} size={26} />
        <div className="min-w-0">
          <strong>{s.symbol}</strong>
          <span className="snapshot-sub">{assetLabel}</span>
        </div>
      </div>
      <div className="market-chip-right">
        <div className="snapshot-price-group">
          <div className="price">{formatPrice(s.last)}</div>
          <span className={`market-delta ${Number.isFinite(change) ? change >= 0 ? 'positive' : 'negative' : 'muted'}`}>
            {Number.isFinite(change) ? `≈ ${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : 'No change %'}
          </span>
        </div>
        <IconButton label={`Refresh ${s.symbol} snapshot`} disabled={disabled} onClick={() => onFetch(s.symbol)}>
          <RefreshCw size={12} />
        </IconButton>
      </div>
    </div>
    <details className="snapshot-meta">
      <summary>Source details <ChevronDown size={11} /></summary>
      <dl>
        {[['Provider', s.provider], ['Exchange', s.exchange], ['Source time', s.source_timestamp], ['Timezone', s.timezone], ['Retrieved', s.fetched_at], ['Change baseline', s.change_baseline]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
    </details>
  </article>
}

interface TurnSnapshot {
  symbol: string
  last: string
  change: string | null
  low: string | null
  high: string | null
  provider: string
  timestamp: string | null
  currency: string | null
  period: string | null
}

function extractTurnSnapshots(evidence: Evidence[]): TurnSnapshot[] {
  const rows: TurnSnapshot[] = []
  for (const item of evidence) {
    if (item.tool !== 'crypto_data_tool' || item.failed) continue
    const context = item.data.field_context && typeof item.data.field_context === 'object' ? item.data.field_context as Record<string, unknown> : {}
    const symbols = Array.isArray(item.data.symbols) ? item.data.symbols : []
    for (const raw of symbols) {
      if (!raw || typeof raw !== 'object') continue
      const coin = raw as Record<string, unknown>
      if (!coin.symbol || !coin.last) continue
      rows.push({
        symbol: String(coin.symbol),
        last: String(coin.last),
        change: coin.daily_change_percentage != null ? String(coin.daily_change_percentage) : null,
        low: coin.lowest != null ? String(coin.lowest) : null,
        high: coin.highest != null ? String(coin.highest) : null,
        provider: typeof item.data.provider === 'string' ? item.data.provider : 'Source data',
        timestamp: coin.date != null ? String(coin.date) : null,
        currency: typeof context.quote_currency === 'string' ? context.quote_currency : null,
        period: typeof context.lowest_highest_period === 'string' ? context.lowest_highest_period : null,
      })
    }
  }
  return rows
}

function ReplySnapshotMetrics({ snapshot: s }: { snapshot: TurnSnapshot }) {
  const change = s.change !== null ? Number(s.change) : NaN
  return (
    <section className="reply-chart-card" aria-label={`${s.symbol} reported snapshot`}>
      <div className="reply-chart-asset"><CoinLogo symbol={s.symbol} size={20} /><strong>{s.symbol}</strong></div>
      <div className="summary-strip mb-0">
        <div><span className="summary-metric-label">Last reported price</span><span className="summary-metric-value">{formatPrice(s.last)}</span></div>
        <div><span className="summary-metric-label">Reported change</span><span className={`summary-metric-value ${Number.isFinite(change) ? change >= 0 ? 'positive' : 'negative' : ''}`}>{Number.isFinite(change) ? `≈ ${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : 'Not provided'}</span></div>
        <div><span className="summary-metric-label">Reported low / high</span><span className="small">{s.low && s.high ? `${formatPrice(s.low)} – ${formatPrice(s.high)}` : 'Not provided'}</span></div>
      </div>
      <p className="tiny muted mt-2">Quote: {s.currency || 'Not specified'} · Low/high period: {s.period || 'Not specified'}</p>
      <p className="tiny muted">Snapshot only. Historical price data is not available.</p>
    </section>
  )
}

function extractTurnArticles(evidence: Evidence[]) {
  const links: Array<{ title: string; source: string; url: string }> = []
  for (const item of evidence) {
    if (item.tool !== 'crypto_news_tool' || item.failed) continue
    const articles = Array.isArray(item.data.articles) ? item.data.articles : []
    for (const raw of articles) {
      if (!raw || typeof raw !== 'object') continue
      const a = raw as Record<string, unknown>
      const url = typeof a.url === 'string' ? safeUrl(a.url) : undefined
      if (url && typeof a.title === 'string') {
        links.push({
          title: a.title,
          source: typeof a.source === 'string' && a.source.trim() ? a.source : 'Source article',
          url,
        })
      }
    }
  }
  return links
}

function buildReplyTitle(turn: Turn, snapshots: ReturnType<typeof extractTurnSnapshots>, articles: ReturnType<typeof extractTurnArticles>): { title: string; subtitle: string } {
  if (snapshots.length === 1) {
    const sym = snapshots[0].symbol
    const name = ASSET_NAMES[sym]
    return {
      title: name ? `${name} (${sym}) Market Analysis` : `${sym} Market Analysis`,
      subtitle: 'Source-grounded snapshot and context from your latest request.',
    }
  }
  if (snapshots.length > 1) {
    return {
      title: `${snapshots.map(s => s.symbol).join(' & ')} Market Snapshot`,
      subtitle: 'Side-by-side reported metrics preserving original units and timestamps.',
    }
  }
  if (articles.length > 0) {
    return {
      title: 'Crypto News Brief',
      subtitle: 'Recent headlines and source attribution matching your query.',
    }
  }
  return {
    title: 'Crypto Research AI',
    subtitle: turn.evidence.length ? 'Source-backed research summary.' : 'Conversational analysis.',
  }
}

export function StructuredReply({ turn, mode, onExport, exportDisabled }: {
  turn: Turn; mode: Mode; onExport?: () => void; exportDisabled?: boolean
}) {
  const snapshots = extractTurnSnapshots(turn.evidence)
  const articles = extractTurnArticles(turn.evidence)
  const providers = [...new Set(turn.evidence.map(item => item.data.provider).filter((v): v is string => typeof v === 'string'))]
  const { title, subtitle } = buildReplyTitle(turn, snapshots, articles)

  return (
    <article className="assistant-message">
      <div className="reply-header">
        <span className="reply-avatar" aria-hidden="true"><BrandLogo size={16} /></span>
        <div className="min-w-0 flex-1">
          <div className="reply-title">{title}</div>
          <div className="reply-subtitle">{subtitle}</div>
        </div>
        <span className="tiny muted shrink-0">{mode === 'demo' ? 'Demo' : 'Source-aware'}</span>
      </div>

      {snapshots.length === 1 && <ReplySnapshotMetrics snapshot={snapshots[0]} />}

      {snapshots.length > 1 && (
        <div className="reply-snapshot-box">
          <div className="reply-snapshot-title">
            <BarChart3 size={14} /> Market Snapshot
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Asset</th>
                  <th scope="col">Last reported</th>
                  <th scope="col">Reported change</th>
                  <th scope="col">Reported range</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.map(s => {
                  const change = s.change !== null ? Number(s.change) : NaN
                  return (
                    <tr key={s.symbol}>
                      <td><div className="flex items-center gap-2"><CoinLogo symbol={s.symbol} size={20} /><strong>{s.symbol}</strong></div></td>
                      <td>{formatPrice(s.last)}</td>
                      <td className={Number.isFinite(change) ? change >= 0 ? 'positive' : 'negative' : 'muted'}>
                        {Number.isFinite(change) ? `≈ ${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : 'Not provided'}
                      </td>
                      <td>{s.low && s.high ? `${formatPrice(s.low)} – ${formatPrice(s.high)}` : 'Not provided'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Markdown content={turn.reply} />

      {(providers.length > 0 || articles.length > 0 || onExport) && (
        <div className="inline-sources-bar">
          {(providers.length > 0 || articles.length > 0) && (
            <span className="inline-sources-label"><Link2 size={13} /> Sources</span>
          )}
          {articles.slice(0, 3).map((article, idx) => (
            <a key={`${article.url}-${idx}`} href={article.url} target="_blank" rel="noopener noreferrer" className="source-chip">
              {article.source} <ArrowUpRight size={11} />
            </a>
          ))}
          {!articles.length && providers.map(provider => (
            <span key={provider} className="source-chip">
              <ShieldCheck size={11} /> {provider}
            </span>
          ))}
          {onExport && (
            <button type="button" className="button compact ml-auto" onClick={onExport} disabled={exportDisabled}>
              <ArrowDownToLine size={12} /> Export
            </button>
          )}
        </div>
      )}

      <SourceDetails evidence={turn.evidence} elapsed={turn.elapsed} />
    </article>
  )
}

function sourceInitials(source: string | null): string {
  if (!source) return 'NW'
  const words = source.trim().split(/\s+/).filter(Boolean)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

function selectNewsThumbnail(article: Article, index: number, preview: boolean): string {
  if (preview) return [btcThumb, ethThumb, instThumb][index % 3]
  const haystack = `${article.title} ${article.query}`.toLowerCase()
  if (/eth|ethereum|ether/.test(haystack)) return ethThumb
  if (/institution|etf|market|stable|regulat|bank|fund/.test(haystack)) return instThumb
  if (/btc|bitcoin/.test(haystack)) return index % 3 === 0 ? btcThumb : [btcThumb, instThumb, ethThumb][index % 3]
  return [btcThumb, ethThumb, instThumb][index % 3]
}

function NewsThumbnail({ article, index, preview }: { article: Article; index: number; preview: boolean }) {
  const [failed, setFailed] = useState(false)
  const src = selectNewsThumbnail(article, index, preview)
  return (
    <span className="news-thumb-wrap">
      {!failed ? (
        <img
          src={src}
          alt=""
          aria-hidden="true"
          title="Illustrative image, not supplied by the article publisher"
          className="news-thumb-img"
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="news-thumb-fallback" aria-hidden="true">{sourceInitials(article.source)}</span>
      )}
    </span>
  )
}

export function NewsList({ articles, preview, max = 3 }: { articles: Article[]; preview: boolean; max?: number }) {
  if (!articles.length) return <EmptyState icon={<FileText size={20} />} title="Follow the story" text="Request news to see headlines, publication times and original links here." />
  return <div className="news-list">
    {preview && <p className="tiny muted pb-1">Fictional example headlines</p>}
    {articles.slice(0, max).map((article, index) => {
      const href = safeUrl(article.url)
      return <article className="news-article" key={`${article.url}-${index}`}>
        <NewsThumbnail article={article} index={index} preview={preview} />
        <div className="news-body">
          {href ? <a href={href} target="_blank" rel="noopener noreferrer" className="news-title">{article.title}</a> : <h3 className="news-title">{article.title}</h3>}
          <p className="news-meta">{article.source || 'Publisher not provided'} · {article.publishedAt || 'Time not provided'}</p>
        </div>
        {href && (
          <a href={href} target="_blank" rel="noopener noreferrer" className="news-ext-icon" aria-label={`Open ${article.title}`}>
            <ArrowUpRight size={15} />
          </a>
        )}
      </article>
    })}
  </div>
}

export function Comparison({ snapshots, compact = false }: { snapshots: Snapshot[]; compact?: boolean }) {
  if (!snapshots.length) return <EmptyState icon={<Database size={20} />} title="Put the data side by side" text="Fetch two assets to compare their reported metrics and provenance." />
  const fields: [keyof Snapshot, string][] = [['last', 'Last reported'], ['change', 'Reported change (%)'], ['low', 'Reported low'], ['high', 'Reported high'], ['quote_currency', 'Quote currency']]
  const metadata: [keyof Snapshot, string][] = [['source_timestamp', 'Source timestamp'], ['timezone', 'Timezone'], ['period', 'Low/high period'], ['change_baseline', 'Change baseline'], ['provider', 'Provider'], ['exchange', 'Exchange'], ['fetched_at', 'Retrieved at']]
  const table = (rows: typeof fields) => <div className="table-scroll"><table className="comparison-table"><thead><tr><th scope="col">Metric</th>{snapshots.map(s => <th scope="col" key={s.symbol}>{s.symbol}</th>)}</tr></thead><tbody>{rows.map(([key, label]) => <tr key={key}><th scope="row">{label}</th>{snapshots.map(s => <td key={s.symbol}>{s[key] ?? 'Not provided'}</td>)}</tr>)}</tbody></table></div>
  return <>{table(fields)}<p className="tiny muted mt-2">Compare performance only when currency, periods and baselines match. Source times may differ.</p>{!compact && <details className="source-details"><summary>Times & provenance <ChevronDown size={13} /></summary>{table(metadata)}</details>}</>
}

export function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="empty-state"><span className="empty-icon">{icon}</span><h3>{title}</h3><p>{text}</p></div>
}

export function ErrorBanner({ message, onDismiss, onRefresh }: { message: string; onDismiss: () => void; onRefresh: () => void }) {
  return <div role="alert" className="error-banner"><TriangleAlert size={17} /><div><strong>Something needs attention</strong><p>{message}</p><div className="flex gap-4 mt-2"><button onClick={onRefresh}>Refresh conversation</button><button onClick={onDismiss}>Dismiss</button></div></div></div>
}

export function ReportView({ turn, onDownload, disabled }: { turn: Turn; onDownload: () => void; disabled: boolean }) {
  return <article className="panel report-panel"><div className="panel-heading"><div><h2>Research report</h2><p>{turn.query}</p></div><button className="button" disabled={disabled} onClick={onDownload}><ArrowDownToLine size={15} />Download Markdown</button></div><Markdown content={turn.reply} /><SourceDetails evidence={turn.evidence} elapsed={turn.elapsed} /></article>
}
