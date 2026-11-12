export type Mode = 'demo' | 'live'
export type View = 'desk' | 'conversations' | 'compare' | 'news' | 'reports'
export interface Evidence {
  tool: string
  args: Record<string, unknown>
  data: Record<string, unknown>
  failed: boolean
}
export interface Snapshot {
  symbol: string; last: string; change: string | null; low: string | null; high: string | null
  quote_currency: string; source_timestamp: string; timezone: string; period: string
  change_baseline: string; exchange: string; provider: string; fetched_at: string
}
export interface Article {
  title: string; source: string | null; url: string; publishedAt: string | null
  query: string; provider: string | null; fetched_at: string | null
}
export interface SourceData {
  snapshots: Snapshot[]; articles: Article[]; coins: { symbol: string; name: string }[]; evidence: Evidence[]
}
export interface Turn {
  id: string; query: string; reply: string; evidence: Evidence[]; elapsed: number; created_at: string
}
export interface SessionSummary {
  id: string; mode: Mode; title: string; created_at: string; updated_at: string; turn_count: number
}
export interface Session extends SessionSummary { turns: Turn[]; latest: SourceData; busy: boolean }
