import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowDownToLine, ArrowUpRight, ChevronDown, Database, FileText, Link2, RefreshCw, Search, TriangleAlert } from 'lucide-react'
import type { Article, Evidence, Snapshot, SourceData, Turn } from './types'

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
  if (!evidence.length) return <p className="tiny muted mt-3">Conversational reply · no tools used for this turn</p>
  const providers = [...new Set(evidence.map(item => item.data.provider).filter(value => typeof value === 'string'))] as string[]
  return <details className="source-details"><summary><Link2 size={13} /> Sources & tools <span className="counter">{evidence.length}</span><ChevronDown size={13} className="ml-auto" /></summary>
    <div className="source-content">
      <div className="flex flex-wrap gap-2">{providers.map(provider => <span className="source-tag" key={provider}>{provider}</span>)}</div>
      {elapsed !== undefined && <p className="tiny muted my-3">Completed in {elapsed.toFixed(1)}s · source results, not private model reasoning</p>}
      {evidence.map((item, index) => <details className="raw-result" key={index}>
        <summary><Database size={12} />{item.tool}<span className={item.failed ? 'negative' : 'muted'}>{item.failed ? 'Failed' : 'Returned'}</span></summary>
        <pre>{JSON.stringify({ arguments: item.args, response: item.data }, null, 2)}</pre>
      </details>)}
    </div>
  </details>
}

export function SnapshotCards({ data, disabled, onFetch, onAssets, preview }: {
  data: SourceData; disabled: boolean; onFetch: (symbol: string) => void; onAssets: () => void; preview: boolean
}) {
  const snapshots = data.snapshots.slice(0, 4)
  return <section aria-label="Market snapshots" className="snapshot-section">
    <div className="section-label"><span>MARKET SNAPSHOT</span><span>{preview ? 'Fictional sample preview' : 'Latest completed request · on demand'}</span></div>
    <div className="snapshot-grid">
      {snapshots.length ? snapshots.map(snapshot => <SnapshotCard key={snapshot.symbol} snapshot={snapshot} disabled={disabled} onFetch={onFetch} />)
        : ['BTC', 'ETH'].map(symbol => <article className="snapshot-card empty-snapshot" key={symbol}>
          <div className="flex items-center gap-2"><span className={`coin coin-${symbol.toLowerCase()}`}>{symbol === 'BTC' ? '₿' : 'Ξ'}</span><strong>{symbol}</strong></div>
          <p className="muted small my-2">No snapshot in this request</p>
          <button className="text-button" disabled={disabled} onClick={() => onFetch(symbol)}>Fetch {symbol} <ArrowUpRight size={13} /></button>
        </article>)}
      <article className="snapshot-card explore-card">
        <span className="subtle-icon"><Search size={17} /></span>
        <div><h3>Find your next question.</h3><p className="muted tiny">Explore the source's available assets.</p></div>
        <button className="text-button" disabled={disabled} onClick={onAssets}>Browse assets <ArrowUpRight size={13} /></button>
      </article>
    </div>
  </section>
}

function SnapshotCard({ snapshot: s, disabled, onFetch }: { snapshot: Snapshot; disabled: boolean; onFetch: (symbol: string) => void }) {
  const change = s.change !== null ? Number(s.change) : NaN
  const knownCurrency = s.quote_currency && !/not specified/i.test(s.quote_currency)
  return <article className="snapshot-card">
    <div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2"><span className={`coin coin-${s.symbol.toLowerCase()}`}>{s.symbol === 'BTC' ? '₿' : s.symbol === 'ETH' ? 'Ξ' : s.symbol[0]}</span><strong>{s.symbol}</strong><span className="tiny muted">{knownCurrency ? s.quote_currency.replace(' (fictional sample)', ' · sample') : 'Quote unspecified'}</span></div>
      <IconButton label={`Refresh ${s.symbol} snapshot`} disabled={disabled} onClick={() => onFetch(s.symbol)}><RefreshCw size={13} /></IconButton></div>
    <div className="price">{formatPrice(s.last)}</div>
    <div className="flex items-center gap-2"><span className={Number.isFinite(change) ? change >= 0 ? 'change positive' : 'change negative' : 'change muted'}>{Number.isFinite(change) ? `≈ ${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : 'Not provided'}</span><span className="tiny muted">reported change</span></div>
    <details className="snapshot-meta"><summary>Source details <ChevronDown size={11} /></summary><dl>
      {[['Provider', s.provider], ['Exchange', s.exchange], ['Source time', s.source_timestamp], ['Timezone', s.timezone], ['Retrieved', s.fetched_at], ['Change baseline', s.change_baseline]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl></details>
  </article>
}

export function NewsList({ articles, preview, max = 3 }: { articles: Article[]; preview: boolean; max?: number }) {
  if (!articles.length) return <EmptyState icon={<FileText size={22} />} title="Follow the story" text="Request news to see headlines, publication times and original links here." />
  return <div className="news-list">{preview && <p className="tiny muted pb-1">Fictional example headlines</p>}{articles.slice(0, max).map((article, index) => {
    const href = safeUrl(article.url)
    return <article className="news-article" key={`${article.url}-${index}`}><span className="news-index">{String(index + 1).padStart(2, '0')}</span><div>
      {href ? <a href={href} target="_blank" rel="noopener noreferrer" className="news-title">{article.title}<ArrowUpRight size={14} /></a> : <h3 className="news-title">{article.title}</h3>}
      <p className="news-meta">{article.source || 'Publisher not provided'}</p><p className="tiny muted" title={article.publishedAt || undefined}>{article.publishedAt || 'Publication time not provided'}</p>
    </div></article>
  })}</div>
}

export function Comparison({ snapshots, compact = false }: { snapshots: Snapshot[]; compact?: boolean }) {
  if (!snapshots.length) return <EmptyState icon={<Database size={22} />} title="Put the data side by side" text="Fetch two assets to compare their reported metrics and provenance." />
  const fields: [keyof Snapshot, string][] = [['last', 'Last reported'], ['change', 'Reported change (%)'], ['low', 'Reported low'], ['high', 'Reported high'], ['quote_currency', 'Quote currency']]
  const metadata: [keyof Snapshot, string][] = [['source_timestamp', 'Source timestamp'], ['timezone', 'Timezone'], ['period', 'Low/high period'], ['change_baseline', 'Change baseline'], ['provider', 'Provider'], ['exchange', 'Exchange'], ['fetched_at', 'Retrieved at']]
  const table = (rows: typeof fields) => <div className="table-scroll"><table className="comparison-table"><thead><tr><th scope="col">Metric</th>{snapshots.map(s => <th scope="col" key={s.symbol}>{s.symbol}</th>)}</tr></thead><tbody>{rows.map(([key, label]) => <tr key={key}><th scope="row">{label}</th>{snapshots.map(s => <td key={s.symbol}>{s[key] ?? 'Not provided'}</td>)}</tr>)}</tbody></table></div>
  return <>{table(fields)}<p className="tiny muted mt-3">Compare performance only when currency, periods and baselines match. Source times may differ.</p>{!compact && <details className="source-details"><summary>Times & provenance <ChevronDown size={13} /></summary>{table(metadata)}</details>}</>
}

export function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="empty-state"><span className="empty-icon">{icon}</span><h3>{title}</h3><p>{text}</p></div>
}

export function ErrorBanner({ message, onDismiss, onRefresh }: { message: string; onDismiss: () => void; onRefresh: () => void }) {
  return <div role="alert" className="error-banner"><TriangleAlert size={18} /><div><strong>Something needs attention</strong><p>{message}</p><div className="flex gap-4 mt-2"><button onClick={onRefresh}>Refresh conversation</button><button onClick={onDismiss}>Dismiss</button></div></div></div>
}

export function ReportView({ turn, onDownload, disabled }: { turn: Turn; onDownload: () => void; disabled: boolean }) {
  return <article className="panel report-panel"><div className="panel-heading"><div><h2>Research report</h2><p>{turn.query}</p></div><button className="button" disabled={disabled} onClick={onDownload}><ArrowDownToLine size={15} />Download Markdown</button></div><Markdown content={turn.reply} /><SourceDetails evidence={turn.evidence} elapsed={turn.elapsed} /></article>
}
