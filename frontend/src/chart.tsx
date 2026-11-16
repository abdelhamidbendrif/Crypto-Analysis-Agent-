import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from './api'
import type { ChartData } from './types'

const dateLabel = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })
const observationLabel = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' })
const axisPrice = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 })
const dollarPrice = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

function timeLabel(value: number) {
  return observationLabel.format(value) + ' UTC'
}

export function PriceChart({ symbol, days, demo }: { symbol: string; days: number; demo: boolean }) {
  const [data, setData] = useState<ChartData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [auto, setAuto] = useState(false)
  const activeRequest = useRef<AbortController | null>(null)
  const gradient = useId()

  const refresh = useCallback(async () => {
    if (activeRequest.current) return
    const controller = new AbortController()
    activeRequest.current = controller
    setLoading(true)
    try {
      const result = await api.chart(symbol, days, demo, controller.signal)
      if (result.fictional !== demo || result.symbol !== symbol) {
        throw new Error('The chart response did not match the selected asset and mode.')
      }
      if (!controller.signal.aborted) {
        setData(result)
        setError('')
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Chart data is unavailable.')
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null
        setLoading(false)
      }
    }
  }, [symbol, days, demo])

  useEffect(() => {
    void refresh()
    return () => {
      activeRequest.current?.abort()
      activeRequest.current = null
    }
  }, [refresh])

  const interval = data?.refresh_seconds
  useEffect(() => {
    if (!auto || !interval || demo) return
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh()
    }, interval * 1000)
    return () => window.clearInterval(timer)
  }, [auto, demo, interval, refresh])

  const points = data?.points.map(point => ({ price: point.price, time: Date.parse(point.timestamp) })) ?? []
  const latest = points.at(-1)
  const formatXAxis = (value: number) => days === 1
    ? new Date(value).toISOString().slice(11, 16)
    : dateLabel.format(value)

  return (
    <div className="chart-panel">
      <div className="chart-meta">
        <strong>{data?.pair || symbol + '/USD'}</strong>
        <span>{demo ? 'Fictional sample data' : 'CoinGecko · aggregated USD prices'}</span>
      </div>
      {!demo && <div className="chart-actions">
        <button className="button compact" disabled={loading} onClick={() => void refresh()}>Refresh history</button>
        {interval && <label className="chart-auto">
          <input type="checkbox" checked={auto} onChange={event => setAuto(event.target.checked)} />
          Auto-refresh every {interval / 60} min while visible
        </label>}
      </div>}
      {loading && <p className="small muted" role="status">{data ? 'Refreshing chart…' : 'Loading price history…'}</p>}
      {error && <div role="alert" className="chart-error">
        <p>{error}</p>
        {data && <p>Showing the last successful response.</p>}
        {demo && <button className="button compact" disabled={loading} onClick={() => void refresh()}>Retry</button>}
      </div>}
      {latest && data && <>
        <div className="chart-plot" aria-label={`${symbol} USD price history`}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <AreaChart data={points} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis type="number" dataKey="time" domain={['dataMin', 'dataMax']}
                tickFormatter={formatXAxis} minTickGap={22} tick={{ fill: 'var(--muted)', fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} width={48} tickFormatter={value => '$' + axisPrice.format(value)}
                tick={{ fill: 'var(--muted)', fontSize: 10 }} />
              <Tooltip labelFormatter={value => timeLabel(Number(value))}
                formatter={value => [dollarPrice.format(Number(value)), 'USD']}
                contentStyle={{ background: 'var(--surface)', color: 'var(--ink)', borderColor: 'var(--border)' }} />
              <Area type="linear" dataKey="price" stroke="var(--accent)" fill={`url(#${gradient})`}
                isAnimationActive={false} dot={points.length === 1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="tiny muted">Latest observation {dollarPrice.format(latest.price)} · {timeLabel(latest.time)}</p>
        {!demo && <p className="tiny muted">Retrieved {timeLabel(Date.parse(data.fetched_at))} · Provider cadence varies</p>}
      </>}
      {!latest && !loading && !error && <p className="small muted">No observations for this range.</p>}
    </div>
  )
}
