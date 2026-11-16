import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StructuredReply } from './components'
import type { Turn } from './types'

const turn: Turn = {
  id: 'source-turn', query: 'BTC snapshot', reply: 'Original source report.', created_at: '2026-01-01', elapsed: .2,
  evidence: [{ tool: 'crypto_data_tool', args: { symbol: 'BTC' }, failed: false, data: {
    provider: 'FreeCryptoAPI', symbols: [{ symbol: 'BTC', last: '75000.01234567', lowest: '74000', highest: '76000', daily_change_percentage: '1.23456' }],
    field_context: { quote_currency: 'not specified in this API response', lowest_highest_period: 'not specified in this API response' },
  } }],
}

describe('Structured source replies', () => {
  it('shows source metrics without inventing historical price curves or metadata', () => {
    render(<StructuredReply turn={turn} mode="live" />)
    expect(screen.getByText('75,000.01234567')).toBeInTheDocument()
    expect(screen.getByText('74,000 – 76,000')).toBeInTheDocument()
    expect(screen.getByText('Single snapshot from the market data provider.')).toBeInTheDocument()
    expect(screen.getByText(/Quote: not specified in this API response/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Curve' })).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /price curve/ })).not.toBeInTheDocument()
    expect(screen.getByText('Original source report.')).toBeInTheDocument()
  })

  it('keeps unavailable quote and period metadata explicit', () => {
    const unknown = { ...turn, evidence: [{ ...turn.evidence[0], data: { ...turn.evidence[0].data, field_context: {} } }] }
    render(<StructuredReply turn={unknown} mode="live" />)
    expect(screen.getByText('Quote: Not specified · Low/high period: Not specified')).toBeInTheDocument()
    expect(screen.queryByText(/24.hour/i)).not.toBeInTheDocument()
  })
})
