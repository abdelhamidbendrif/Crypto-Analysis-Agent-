import express, { Request, Response, NextFunction } from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import path from 'path'
import { fileURLToPath } from 'url'
import { randomUUID } from 'crypto'

dotenv.config()

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const SAMPLE_TIME = '2026-01-01T12:00:00+00:00'

interface SampleMarket {
  symbol: string
  last: string
  last_btc: string
  lowest: string
  highest: string
  daily_change_percentage: string
  date: string
  source_exchange: string
}

const SAMPLE_MARKETS: Record<string, SampleMarket> = {
  BTC: {
    symbol: 'BTC',
    last: '75000.00',
    last_btc: '1',
    lowest: '73500.00',
    highest: '75800.00',
    daily_change_percentage: '1.25',
    date: SAMPLE_TIME,
    source_exchange: 'Simulated exchange',
  },
  ETH: {
    symbol: 'ETH',
    last: '2500.00',
    last_btc: '0.03333333',
    lowest: '2420.00',
    highest: '2540.00',
    daily_change_percentage: '0.80',
    date: SAMPLE_TIME,
    source_exchange: 'Simulated exchange',
  },
}

const SAMPLE_CONTEXT = {
  quote_currency: 'USD (fictional sample)',
  timestamp_timezone: 'UTC (fictional sample)',
  lowest_highest_period: '24 hours (fictional sample)',
  percentage_change_baseline: '24 hours earlier (fictional sample)',
}

const UNKNOWN_CONTEXT = {
  quote_currency: 'not specified in this API response',
  timestamp_timezone: 'not specified in this API response',
  lowest_highest_period: 'not specified in this API response',
  percentage_change_baseline: 'not specified in this API response',
}

interface Evidence {
  tool: string
  args: Record<string, unknown>
  data: Record<string, unknown>
  failed: boolean
}

interface Snapshot {
  symbol: string
  last: string
  change: string | null
  low: string | null
  high: string | null
  quote_currency: string
  source_timestamp: string
  timezone: string
  period: string
  change_baseline: string
  exchange: string
  provider: string
  fetched_at: string
}

interface Article {
  title: string
  source: string | null
  url: string
  publishedAt: string | null
  query: string
  provider: string | null
  fetched_at: string | null
}

interface SourceData {
  snapshots: Snapshot[]
  articles: Article[]
  coins: { symbol: string; name: string }[]
  evidence: Evidence[]
}

interface Turn {
  id: string
  query: string
  reply: string
  evidence: Evidence[]
  elapsed: number
  created_at: string
}

interface SessionRecord {
  id: string
  owner: string
  mode: 'demo' | 'live'
  created_at: string
  updated_at: string
  touched: number
  history: Array<{ role: string; content: string; tool_calls?: any[]; tool_call_id?: string; name?: string }>
  turns: Turn[]
  busy: boolean
}

function now(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00')
}

function reportCell(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'Not provided'
  }
  return String(value).replace(/\|/g, '\\|').replace(/\r/g, ' ').replace(/\n/g, ' ')
}

function sampleMarketPayload(symbol: string) {
  return {
    status: 'success',
    provider: 'Demo fixtures — fictional data',
    fetched_at: SAMPLE_TIME,
    symbols: [{ ...SAMPLE_MARKETS[symbol] }],
    field_context: { ...SAMPLE_CONTEXT },
    warnings: ['Simulated showcase data. Not a current market quote.'],
  }
}

function marketRows(evidence: Evidence[]): Array<Record<string, string>> {
  const rows: Array<Record<string, string>> = []
  for (const result of evidence) {
    if (result.tool !== 'crypto_data_tool' || result.failed) continue
    const data = result.data as any
    const context = (data.field_context || {}) as Record<string, string>
    const symbols = (data.symbols || []) as Array<Record<string, any>>
    for (const coin of symbols) {
      rows.push({
        Symbol: String(coin.symbol || ''),
        'Last reported': String(coin.last ?? ''),
        'Reported change (%)': coin.daily_change_percentage != null ? String(coin.daily_change_percentage) : 'Not provided',
        'Reported low': coin.lowest != null ? String(coin.lowest) : 'Not provided',
        'Reported high': coin.highest != null ? String(coin.highest) : 'Not provided',
        'Quote currency': context.quote_currency || 'Not specified',
        'Source timestamp': coin.date || 'Not provided',
        'Timestamp timezone': context.timestamp_timezone || 'Not specified',
        'Low/high period': context.lowest_highest_period || 'Not specified',
        'Change baseline': context.percentage_change_baseline || 'Not specified',
        Exchange: coin.source_exchange || 'Not provided',
        Provider: data.provider || 'Not provided',
        'Retrieved at': data.fetched_at || 'Not provided',
      })
    }
  }
  return rows
}

function sourceViews(evidence: Evidence[]): SourceData {
  const snapshots: Snapshot[] = marketRows(evidence).map(row => ({
    symbol: row.Symbol,
    last: row['Last reported'],
    change: row['Reported change (%)'] !== 'Not provided' ? row['Reported change (%)'] : null,
    low: row['Reported low'] !== 'Not provided' ? row['Reported low'] : null,
    high: row['Reported high'] !== 'Not provided' ? row['Reported high'] : null,
    quote_currency: row['Quote currency'],
    source_timestamp: row['Source timestamp'],
    timezone: row['Timestamp timezone'],
    period: row['Low/high period'],
    change_baseline: row['Change baseline'],
    exchange: row.Exchange,
    provider: row.Provider,
    fetched_at: row['Retrieved at'],
  }))

  const articles: Article[] = []
  const coins: { symbol: string; name: string }[] = []

  for (const result of evidence) {
    if (result.failed) continue
    const data = result.data as any
    if (result.tool === 'crypto_news_tool') {
      const list = (data.articles || []) as any[]
      for (const item of list) {
        articles.push({
          title: item.title || '',
          source: item.source || null,
          url: item.url || '',
          publishedAt: item.publishedAt || null,
          query: String(result.args.query || ''),
          provider: data.provider || null,
          fetched_at: data.fetched_at || null,
        })
      }
    }
    if (result.tool === 'crypto_list_tool') {
      const list = (data.coins || []) as any[]
      for (const item of list) {
        coins.push({
          symbol: String(item.symbol || ''),
          name: String(item.name || ''),
        })
      }
    }
  }

  return { snapshots, articles, coins, evidence }
}

function buildGroundedReport(evidence: Evidence[]): string | null {
  const sections: string[] = []
  const kinds = new Set<string>()
  const marketSnapshots: Record<string, any> = {}
  const newsCounts: string[] = []
  let coinCount = 0

  for (const item of evidence) {
    const name = item.tool
    const args = item.args
    let title = name === 'crypto_list_tool'
      ? 'Available cryptocurrencies'
      : name === 'crypto_data_tool'
      ? 'Market data'
      : name === 'crypto_news_tool'
      ? 'News'
      : 'Source result'

    const query = args.query || args.symbol
    if (query) {
      title += ` - ${reportCell(query)}`
    }

    const data = item.data as any
    if (!data || typeof data !== 'object') {
      sections.push(`### ${title}\nData unavailable: unexpected response structure.`)
      continue
    }

    if (item.failed || data.status === false || data.status === 'error' || data.status === 'failed') {
      const errorMsg = reportCell(data.error || data.message || 'Source request failed')
      sections.push(`### ${title}\nData unavailable: ${errorMsg}`)
      continue
    }

    const lines: string[] = [`### ${title}`]
    if (typeof data.provider === 'string') {
      lines.push(`Data provider: ${reportCell(data.provider)}`)
    }
    if (typeof data.fetched_at === 'string') {
      lines.push(`Retrieved at: ${reportCell(data.fetched_at)}`)
    }
    if (Array.isArray(data.warnings)) {
      for (const warning of data.warnings) {
        if (typeof warning === 'string') {
          lines.push(`- Data quality note: ${reportCell(warning)}`)
        }
      }
    }

    if (name === 'crypto_list_tool' && Array.isArray(data.coins)) {
      const coinList = data.coins.filter((c: any) => c && typeof c === 'object' && c.symbol)
      if (data.coins.length && !coinList.length) {
        sections.push(`### ${title}\nData unavailable: invalid coin records.`)
        continue
      }
      kinds.add('coins')
      coinCount += coinList.length
      lines.push('| Symbol | Name |', '|---|---|')
      for (const c of coinList) {
        lines.push(`| ${reportCell(c.symbol)} | ${reportCell(c.name)} |`)
      }
      if (!coinList.length) {
        lines.push('No coins were returned.')
      }
    } else if (name === 'crypto_data_tool' && Array.isArray(data.symbols)) {
      const snapshots = data.symbols.filter((s: any) => s && typeof s === 'object' && s.symbol)
      if (data.symbols.length && !snapshots.length) {
        sections.push(`### ${title}\nData unavailable: invalid market records.`)
        continue
      }
      kinds.add('market')
      const context = (data.field_context || {}) as Record<string, string>
      for (const coin of snapshots) {
        marketSnapshots[String(coin.symbol)] = coin
        lines.push(
          `\n**${reportCell(coin.symbol)}**`,
          '| Metric | Reported value |',
          '|---|---|',
          `| Last reported price | ${reportCell(coin.last)} |`,
          `| Reported BTC-relative value | ${reportCell(coin.last_btc)} |`,
          `| Reported low | ${reportCell(coin.lowest)} |`,
          `| Reported high | ${reportCell(coin.highest)} |`,
          `| Reported percentage change (%) | ${reportCell(coin.daily_change_percentage)} |`,
          `| Source timestamp | ${reportCell(coin.date)} |`,
          `| Source exchange | ${reportCell(coin.source_exchange)} |`,
        )
      }
      for (const [field, label] of [
        ['quote_currency', 'Quote currency'],
        ['timestamp_timezone', 'Timestamp timezone'],
        ['lowest_highest_period', 'Low/high period'],
        ['percentage_change_baseline', 'Percentage-change baseline'],
      ]) {
        const val = context[field] || 'not specified in this API response'
        lines.push(`\n- ${label}: ${reportCell(val)}`)
      }
      if (!snapshots.length) {
        lines.push('No market snapshots were returned.')
      }
    } else if (name === 'crypto_news_tool' && Array.isArray(data.articles)) {
      const articles = data.articles.filter((a: any) => a && typeof a === 'object' && a.title)
      if (data.articles.length && !articles.length) {
        sections.push(`### ${title}\nData unavailable: invalid article records.`)
        continue
      }
      kinds.add('news')
      newsCounts.push(`${reportCell(query || 'requested topic')}: ${articles.length}`)
      lines.push(`Articles returned: ${articles.length}; total search matches: ${reportCell(data.totalResults)}.`)
      articles.forEach((a: any, idx: number) => {
        lines.push(
          `\n${idx + 1}. **${reportCell(a.title)}**`,
          `   - Source: ${reportCell(a.source)}`,
          `   - Published: ${reportCell(a.publishedAt)}`,
          `   - URL: ${reportCell(a.url)}`,
        )
      })
      if (!articles.length) {
        lines.push('No articles were returned for this query.')
      }
    } else {
      lines.push('Data unavailable: the response does not contain the expected records.')
    }
    sections.push(lines.join('\n'))
  }

  if (!sections.length) return null

  const meaning: string[] = []
  if (kinds.has('market')) {
    if (Object.keys(marketSnapshots).length > 1) {
      const changes = Object.entries(marketSnapshots)
        .filter(([, coin]) => coin.daily_change_percentage != null)
        .map(([sym, coin]) => `${reportCell(sym)}: ${reportCell(coin.daily_change_percentage)}%`)
        .join('; ')
      if (changes) {
        meaning.push(
          `Reported percentage changes: ${changes}. Without confirmed comparison baselines, these figures do not establish a performance ranking.`,
        )
      }
    }
    meaning.push(
      'These are source-reported snapshots. Unspecified units, periods, and comparison baselines remain unknown. These fields alone do not establish liquidity, measured volatility, support/resistance, or future performance.',
    )
  }
  if (kinds.has('news')) {
    meaning.push('Headlines and publication times are copied from the news results; they do not prove why a price moved.')
  }
  if (kinds.has('coins')) {
    meaning.push('Only symbols and names supplied by the data source are listed.')
  }
  if (!meaning.length) {
    meaning.push('The requested evidence was unavailable; no market conclusion can be drawn from these results.')
  }

  const summary: string[] = []
  if (Object.keys(marketSnapshots).length > 0) {
    summary.push('Market snapshots: ' + Object.keys(marketSnapshots).map(reportCell).join(', ') + '.')
  }
  if (newsCounts.length > 0) {
    summary.push('News articles returned - ' + newsCounts.join('; ') + '.')
  }
  if (kinds.has('coins')) {
    summary.push(`Supported coin records returned: ${coinCount}.`)
  }
  if (!summary.length) {
    summary.push('No usable source records were returned. See the source errors below.')
  }

  return (
    '## Summary\n' +
    summary.join(' ') +
    '\n\n## Data\n' +
    sections.join('\n\n') +
    '\n\n## What it means\n' +
    meaning.join('\n\n') +
    '\n\n## Next steps\nAsk for another supported coin\'s market snapshot, relevant news, or the list of supported symbols.'
  )
}

function demoTurn(query: string, previousEvidence: Evidence[]): { reply: string; evidence: Evidence[] } {
  const lower = query.toLowerCase()
  let symbols: string[] = []
  if (/\b(btc|bitcoin)\b/.test(lower)) symbols.push('BTC')
  if (/\b(eth|ethereum|ether)\b/.test(lower)) symbols.push('ETH')

  if (!symbols.length && /\b(same|its|it|that cryptocurrency)\b/.test(lower)) {
    for (let i = previousEvidence.length - 1; i >= 0; i--) {
      const topic = String(previousEvidence[i].args?.symbol || previousEvidence[i].args?.query || '').toLowerCase()
      if (['btc', 'bitcoin', 'eth', 'ethereum'].includes(topic)) {
        symbols = [topic.includes('btc') || topic.includes('bitcoin') ? 'BTC' : 'ETH']
        break
      }
    }
  }

  let wantsNews = /news|article|headline/.test(lower)
  if (!wantsNews && /^\s*(and\s+|what\s+about\s+)?(eth|ethereum|btc|bitcoin)[?.!\s]*$/.test(lower)) {
    wantsNews = previousEvidence.length > 0 && previousEvidence[previousEvidence.length - 1].tool === 'crypto_news_tool'
  }

  const operations: Array<{ name: string; args: Record<string, unknown>; payload: Record<string, unknown> }> = []

  if (/list|available|symbols/.test(lower) && !symbols.length) {
    operations.push({
      name: 'crypto_list_tool',
      args: { limit: 2 },
      payload: {
        status: true,
        provider: 'Demo fixtures — fictional data',
        coins: [
          { symbol: 'BTC', name: 'Bitcoin' },
          { symbol: 'ETH', name: 'Ethereum' },
        ],
      },
    })
  } else if (symbols.length) {
    for (const sym of symbols) {
      if (wantsNews) {
        const name = sym === 'BTC' ? 'Bitcoin' : 'Ethereum'
        const articles = [1, 2, 3].map(idx => ({
          title: `Sample ${name} headline ${idx}: fictional market research`,
          source: 'Sample publisher',
          publishedAt: SAMPLE_TIME,
          url: `https://example.com/demo/${sym.toLowerCase()}/${idx}`,
        }))
        operations.push({
          name: 'crypto_news_tool',
          args: { query: name.toLowerCase(), max_items: 3 },
          payload: {
            status: 'ok',
            provider: 'Demo fixtures — fictional data',
            returned: 3,
            totalResults: 3,
            articles,
            warnings: ['Fictional headlines and example.com links for UI demonstration.'],
          },
        })
      } else {
        operations.push({
          name: 'crypto_data_tool',
          args: { symbol: sym },
          payload: sampleMarketPayload(sym),
        })
      }
    }
  }

  if (operations.length) {
    const evidence: Evidence[] = operations.map(op => ({
      tool: op.name,
      args: op.args,
      data: op.payload,
      failed: false,
    }))
    const reply = buildGroundedReport(evidence) || 'Report generated.'
    return { reply, evidence }
  } else {
    const reply =
      'This is a scripted demo, with fictional BTC and ETH data. ' +
      'Try a market snapshot, compare BTC and ETH, request three sample news articles, ' +
      'or list available symbols. Switch to Live APIs for the real agent.'
    return { reply, evidence: [] }
  }
}

class SessionStore {
  private records = new Map<string, SessionRecord>()
  private ttl = 14400 // 4 hours in seconds
  private maxSessions = 100

  private expire() {
    const nowSec = Date.now() / 1000
    for (const [id, record] of this.records.entries()) {
      if (nowSec - record.touched > this.ttl && !record.busy) {
        this.records.delete(id)
      }
    }
  }

  create(owner: string, mode: 'demo' | 'live' = 'demo'): any {
    this.expire()
    if (this.records.size >= this.maxSessions) {
      throw { status: 429, message: 'Session capacity reached. Restart the local backend or try later.' }
    }
    const id = randomUUID()
    const record: SessionRecord = {
      id,
      owner,
      mode,
      created_at: now(),
      updated_at: now(),
      touched: Date.now() / 1000,
      history: [],
      turns: [],
      busy: false,
    }
    this.records.set(id, record)
    return this.present(record)
  }

  get(owner: string, sessionId: string): SessionRecord {
    this.expire()
    const record = this.records.get(sessionId)
    if (!record || record.owner !== owner) {
      throw { status: 404, message: 'Conversation not found or expired. Start a new conversation.' }
    }
    record.touched = Date.now() / 1000
    return record
  }

  list(owner: string) {
    this.expire()
    const userRecords = Array.from(this.records.values())
      .filter(r => r.owner === owner)
      .sort((a, b) => (b.updated_at > a.updated_at ? 1 : -1))
    return userRecords.map(r => this.summary(r))
  }

  summary(record: SessionRecord) {
    return {
      id: record.id,
      mode: record.mode,
      created_at: record.created_at,
      updated_at: record.updated_at,
      turn_count: record.turns.length,
      title: record.turns.length ? record.turns[0].query.slice(0, 80) : 'New conversation',
    }
  }

  present(record: SessionRecord) {
    const lastTurn = record.turns[record.turns.length - 1]
    const latestEvidence = lastTurn ? lastTurn.evidence : []
    return {
      ...this.summary(record),
      turns: record.turns,
      busy: record.busy,
      latest: sourceViews(latestEvidence),
    }
  }

  async execute(
    owner: string,
    sessionId: string,
    query: string,
    operations?: Array<{ name: string; args: Record<string, unknown> }>,
  ) {
    const record = this.get(owner, sessionId)
    if (record.busy) {
      throw { status: 409, message: 'This conversation is still researching. Wait for the current request.' }
    }
    if (record.turns.length >= 100) {
      throw { status: 409, message: 'Conversation limit reached. Start a new conversation.' }
    }

    record.busy = true
    const startTime = Date.now()

    try {
      let turnReply = ''
      let turnEvidence: Evidence[] = []

      if (record.mode === 'demo') {
        const lastTurn = record.turns[record.turns.length - 1]
        const prevEv = lastTurn ? lastTurn.evidence : []

        if (operations && operations.length) {
          const opsEvidence: Evidence[] = []
          for (const op of operations) {
            if (op.name === 'crypto_data_tool') {
              const sym = String(op.args.symbol || 'BTC').toUpperCase()
              opsEvidence.push({
                tool: op.name,
                args: op.args,
                data: sampleMarketPayload(sym),
                failed: false,
              })
            } else if (op.name === 'crypto_news_tool') {
              const q = String(op.args.query || 'bitcoin')
              const max = Number(op.args.max_items || 3)
              const articles = Array.from({ length: max }, (_, idx) => ({
                title: `Sample ${q} headline ${idx + 1}: fictional market research`,
                source: 'Sample publisher',
                publishedAt: SAMPLE_TIME,
                url: `https://example.com/demo/${q}/${idx + 1}`,
              }))
              opsEvidence.push({
                tool: op.name,
                args: op.args,
                data: {
                  status: 'ok',
                  provider: 'Demo fixtures — fictional data',
                  returned: max,
                  totalResults: max,
                  articles,
                  warnings: ['Fictional headlines and example.com links for UI demonstration.'],
                },
                failed: false,
              })
            } else if (op.name === 'crypto_list_tool') {
              opsEvidence.push({
                tool: op.name,
                args: op.args,
                data: {
                  status: true,
                  provider: 'Demo fixtures — fictional data',
                  coins: [
                    { symbol: 'BTC', name: 'Bitcoin' },
                    { symbol: 'ETH', name: 'Ethereum' },
                  ],
                },
                failed: false,
              })
            }
          }
          turnEvidence = opsEvidence
          turnReply = buildGroundedReport(opsEvidence) || 'Structured research complete.'
        } else {
          const res = demoTurn(query, prevEv)
          turnReply = res.reply
          turnEvidence = res.evidence
        }
      } else {
        // Live Mode
        const freecryptoToken = process.env.FREECRYPTO_TOKEN
        const newsapiKey = process.env.NEWSAPI_KEY

        const liveOps = operations || []
        if (!liveOps.length) {
          // Parse query for symbols
          const lower = query.toLowerCase()
          const matched: string[] = []
          if (/\b(btc|bitcoin)\b/.test(lower)) matched.push('BTC')
          if (/\b(eth|ethereum|ether)\b/.test(lower)) matched.push('ETH')
          if (/\b(ltc|litecoin)\b/.test(lower)) matched.push('LTC')
          if (/\b(bnb|binance)\b/.test(lower)) matched.push('BNB')

          const wantsNews = /news|article|headline/.test(lower)
          if (/list|available|symbols/.test(lower)) {
            liveOps.push({ name: 'crypto_list_tool', args: { limit: 25 } })
          } else if (matched.length) {
            for (const sym of matched) {
              if (wantsNews) {
                liveOps.push({ name: 'crypto_news_tool', args: { query: sym, max_items: 3 } })
              } else {
                liveOps.push({ name: 'crypto_data_tool', args: { symbol: sym } })
              }
            }
          }
        }

        const evidenceCollected: Evidence[] = []

        for (const op of liveOps) {
          if (op.name === 'crypto_data_tool') {
            const sym = String(op.args.symbol || 'BTC').toUpperCase()
            if (freecryptoToken) {
              try {
                const resp = await fetch(`https://api.freecryptoapi.com/v1/getData?symbol=${sym}`, {
                  headers: { Authorization: `Bearer ${freecryptoToken}` },
                })
                const json = await resp.json()
                if (resp.ok && json.symbols) {
                  evidenceCollected.push({
                    tool: op.name,
                    args: op.args,
                    data: {
                      status: 'success',
                      provider: 'FreeCryptoAPI',
                      fetched_at: now(),
                      symbols: json.symbols,
                      field_context: json.field_context || UNKNOWN_CONTEXT,
                    },
                    failed: false,
                  })
                } else {
                  evidenceCollected.push({
                    tool: op.name,
                    args: op.args,
                    data: { status: 'error', error: json.message || 'Data retrieval failed', provider: 'FreeCryptoAPI' },
                    failed: true,
                  })
                }
              } catch (e: any) {
                evidenceCollected.push({
                  tool: op.name,
                  args: op.args,
                  data: { status: 'error', error: e.message, provider: 'FreeCryptoAPI' },
                  failed: true,
                })
              }
            } else {
              evidenceCollected.push({
                tool: op.name,
                args: op.args,
                data: {
                  status: 'error',
                  error: 'FREECRYPTO_TOKEN is not configured in environment. Provide API keys or switch to Demo mode.',
                  provider: 'FreeCryptoAPI',
                },
                failed: true,
              })
            }
          } else if (op.name === 'crypto_news_tool') {
            const q = String(op.args.query || 'bitcoin')
            const max = Math.min(10, Math.max(1, Number(op.args.max_items || 3)))
            if (newsapiKey) {
              try {
                const resp = await fetch(
                  `https://newsapi.org/v2/everything?q=${encodeURIComponent(q)}&language=en&sortBy=publishedAt&pageSize=${max}`,
                  { headers: { 'X-Api-Key': newsapiKey } },
                )
                const json = await resp.json()
                if (resp.ok && json.articles) {
                  evidenceCollected.push({
                    tool: op.name,
                    args: op.args,
                    data: {
                      status: 'ok',
                      provider: 'NewsAPI',
                      fetched_at: now(),
                      totalResults: json.totalResults,
                      articles: json.articles.map((a: any) => ({
                        title: a.title,
                        source: a.source?.name,
                        url: a.url,
                        publishedAt: a.publishedAt,
                      })),
                    },
                    failed: false,
                  })
                } else {
                  evidenceCollected.push({
                    tool: op.name,
                    args: op.args,
                    data: { status: 'error', error: json.message || 'News query failed', provider: 'NewsAPI' },
                    failed: true,
                  })
                }
              } catch (e: any) {
                evidenceCollected.push({
                  tool: op.name,
                  args: op.args,
                  data: { status: 'error', error: e.message, provider: 'NewsAPI' },
                  failed: true,
                })
              }
            } else {
              evidenceCollected.push({
                tool: op.name,
                args: op.args,
                data: {
                  status: 'error',
                  error: 'NEWSAPI_KEY is not configured in environment. Provide API keys or switch to Demo mode.',
                  provider: 'NewsAPI',
                },
                failed: true,
              })
            }
          } else if (op.name === 'crypto_list_tool') {
            if (freecryptoToken) {
              try {
                const resp = await fetch(`https://api.freecryptoapi.com/v1/getCryptoList`, {
                  headers: { Authorization: `Bearer ${freecryptoToken}` },
                })
                const json = await resp.json()
                const coins = (json.result || json || []).slice(0, 25).map((c: any) => ({
                  symbol: c.symbol || c.Symbol || c.ticker,
                  name: c.name || c.Name,
                }))
                evidenceCollected.push({
                  tool: op.name,
                  args: op.args,
                  data: {
                    status: true,
                    provider: 'FreeCryptoAPI',
                    fetched_at: now(),
                    coins,
                  },
                  failed: false,
                })
              } catch (e: any) {
                evidenceCollected.push({
                  tool: op.name,
                  args: op.args,
                  data: { status: 'error', error: e.message, provider: 'FreeCryptoAPI' },
                  failed: true,
                })
              }
            } else {
              evidenceCollected.push({
                tool: op.name,
                args: op.args,
                data: {
                  status: 'error',
                  error: 'FREECRYPTO_TOKEN is not configured in environment. Provide API keys or switch to Demo mode.',
                  provider: 'FreeCryptoAPI',
                },
                failed: true,
              })
            }
          }
        }

        turnEvidence = evidenceCollected
        if (evidenceCollected.length) {
          turnReply = buildGroundedReport(evidenceCollected) || 'Analysis complete.'
        } else {
          turnReply =
            `I received your query: "${query}". To retrieve real-time quotes or news, ask about a supported cryptocurrency (e.g., BTC, ETH) or ensure FREECRYPTO_TOKEN and NEWSAPI_KEY are configured in .env.`
        }
      }

      const elapsed = Math.round((Date.now() - startTime) / 100) / 10
      const turn: Turn = {
        id: randomUUID(),
        query,
        reply: turnReply,
        evidence: turnEvidence,
        elapsed,
        created_at: now(),
      }

      record.turns.push(turn)
      record.updated_at = now()
      record.touched = Date.now() / 1000
      record.busy = false
      return this.present(record)
    } catch (err: any) {
      if (err.status) throw err
      // Context reset on execution failure
      record.turns = []
      record.history = []
      record.updated_at = now()
      throw {
        status: 502,
        detail: {
          message:
            'Research could not be completed. Check the backend API keys, connection and quotas. Conversation context was reset; please retry.',
          context_reset: true,
        },
      }
    } finally {
      record.busy = false
    }
  }

  export(owner: string, sessionId: string, turnId: string): string {
    const record = this.get(owner, sessionId)
    const turn = record.turns.find(t => t.id === turnId)
    if (!turn) {
      throw { status: 404, message: 'Report not found.' }
    }
    const title = record.mode === 'demo' ? 'DEMO — FICTIONAL SAMPLE DATA' : 'Crypto Research AI'
    return `# ${title}\n\n${turn.reply}\n`
  }
}

const store = new SessionStore()

const app = express()

app.use(express.json())

const defaultOrigins =
  'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,http://localhost:3000,http://127.0.0.1:3000'
const allowedOrigins = (process.env.API_CORS_ORIGINS || defaultOrigins)
  .split(',')
  .map(s => s.trim())
  .filter(Boolean)

app.use(
  cors({
    origin: (origin, callback) => {
      if (
        !origin ||
        allowedOrigins.includes(origin) ||
        allowedOrigins.includes('*') ||
        origin.startsWith('http://localhost') ||
        origin.startsWith('http://127.0.0.1')
      ) {
        callback(null, true)
      } else {
        callback(null, false)
      }
    },
    optionsSuccessStatus: 200,
    credentials: false,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'X-Workspace-ID', 'content-type', 'x-workspace-id'],
    exposedHeaders: ['Content-Disposition'],
  }),
)

function getWorkspaceId(req: Request): string {
  const header = req.headers['x-workspace-id']
  if (!header || typeof header !== 'string' || !header.trim()) {
    throw { status: 422, message: 'Missing or invalid X-Workspace-ID header.' }
  }
  return header.trim()
}

function checkDemoSymbols(session: SessionRecord, symbols: string[]) {
  if (session.mode === 'demo' && symbols.some(s => !['BTC', 'ETH'].includes(s))) {
    throw {
      status: 422,
      message: 'The scripted demo supports BTC and ETH only. Use Live APIs for other assets.',
    }
  }
}

// API Routes
app.get('/api/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok' })
})

app.get('/api/demo/preview', (_req: Request, res: Response) => {
  const market = demoTurn('Compare BTC and ETH', [])
  const news = demoTurn('Three news articles about Bitcoin', [])
  const evidence = [...market.evidence, ...news.evidence]
  res.json({
    mode: 'demo',
    fictional: true,
    ...sourceViews(evidence),
  })
})

app.post('/api/sessions', (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const mode = req.body?.mode === 'live' ? 'live' : 'demo'
    const session = store.create(owner, mode)
    res.status(201).json(session)
  } catch (err) {
    next(err)
  }
})

app.get('/api/sessions', (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    res.json(store.list(owner))
  } catch (err) {
    next(err)
  }
})

app.get('/api/sessions/:id', (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const session = store.get(owner, id)
    res.json(store.present(session))
  } catch (err) {
    next(err)
  }
})

app.post('/api/sessions/:id/chat', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const message = req.body?.message
    if (!message || typeof message !== 'string' || !message.trim() || message.length > 2000) {
      throw { status: 422, message: 'Message must be a nonempty string of at most 2000 characters.' }
    }
    const result = await store.execute(owner, id, message.trim())
    res.json(result)
  } catch (err) {
    next(err)
  }
})

app.post('/api/sessions/:id/market', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const session = store.get(owner, id)
    const rawSymbols = req.body?.symbols
    if (!Array.isArray(rawSymbols) || !rawSymbols.length || rawSymbols.length > 4) {
      throw { status: 422, message: 'Provide 1 to 4 cryptocurrency symbols.' }
    }
    const symbols = Array.from(new Set(rawSymbols.map((s: any) => String(s || '').trim().toUpperCase()))).filter(
      Boolean,
    )
    if (!symbols.length || symbols.some(s => s.length > 100 || /[\x00-\x1F]/.test(s))) {
      throw { status: 422, message: 'Use nonempty cryptocurrency symbols of at most 100 characters.' }
    }
    checkDemoSymbols(session, symbols)
    const query = `Give me current market data for ${symbols.join(', ')}. Preserve source units and timestamps.`
    const ops = symbols.map(sym => ({ name: 'crypto_data_tool', args: { symbol: sym } }))
    const result = await store.execute(owner, id, query, ops)
    res.json(result)
  } catch (err) {
    next(err)
  }
})

app.post('/api/sessions/:id/compare', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const session = store.get(owner, id)
    const rawSymbols = req.body?.symbols
    if (!Array.isArray(rawSymbols) || rawSymbols.length < 2 || rawSymbols.length > 4) {
      throw { status: 422, message: 'Choose at least two different assets.' }
    }
    const symbols = Array.from(new Set(rawSymbols.map((s: any) => String(s || '').trim().toUpperCase()))).filter(
      Boolean,
    )
    if (symbols.length < 2) {
      throw { status: 422, message: 'Choose at least two different assets.' }
    }
    checkDemoSymbols(session, symbols)
    const query = `Compare current market data for ${symbols.join(' and ')}. Preserve source units and timestamps.`
    const ops = symbols.map(sym => ({ name: 'crypto_data_tool', args: { symbol: sym } }))
    const result = await store.execute(owner, id, query, ops)
    res.json(result)
  } catch (err) {
    next(err)
  }
})

app.post('/api/sessions/:id/news', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const query = req.body?.query
    if (!query || typeof query !== 'string' || !query.trim() || query.length > 150) {
      throw { status: 422, message: 'Provide search keywords between 1 and 150 characters.' }
    }
    const maxItems = Number(req.body?.max_items ?? 3)
    if (isNaN(maxItems) || maxItems < 1 || maxItems > 10) {
      throw { status: 422, message: 'max_items must be between 1 and 10.' }
    }
    const cleanQuery = query.trim()
    const prompt = `Give me ${maxItems} recent news articles about ${cleanQuery}.`
    const ops = [{ name: 'crypto_news_tool', args: { query: cleanQuery, max_items: maxItems } }]
    const result = await store.execute(owner, id, prompt, ops)
    res.json(result)
  } catch (err) {
    next(err)
  }
})

app.post('/api/sessions/:id/assets', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const query = 'List 25 available cryptocurrencies and their symbols.'
    const ops = [{ name: 'crypto_list_tool', args: { limit: 25 } }]
    const result = await store.execute(owner, id, query, ops)
    res.json(result)
  } catch (err) {
    next(err)
  }
})

app.get('/api/sessions/:id/reports/:turnId', (req: Request, res: Response, next: NextFunction) => {
  try {
    const owner = getWorkspaceId(req)
    const id = String(req.params.id)
    const turnId = String(req.params.turnId)
    const content = store.export(owner, id, turnId)
    res.setHeader('Content-Type', 'text/markdown; charset=utf-8')
    res.setHeader('Content-Disposition', 'attachment; filename="crypto-research-report.md"')
    res.send(content)
  } catch (err) {
    next(err)
  }
})

// Error handling middleware
app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  const status = err.status || 500
  const detail = err.detail || err.message || 'Internal Server Error'
  res.status(status).json({ detail })
})

// Vite / static file serving
const isProduction = process.env.NODE_ENV === 'production'
const PORT = 3000
const HOST = '0.0.0.0'

async function startServer() {
  if (!isProduction) {
    const { createServer: createViteServer } = await import('vite')
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    })
    app.use(vite.middlewares)
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')))
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'))
    })
  }

  app.listen(PORT, HOST, () => {
    console.log(`Server listening on http://${HOST}:${PORT}`)
  })
}

startServer().catch(err => {
  console.error('Failed to start server:', err)
  process.exit(1)
})
