import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'

const web = process.env.WEB_URL || 'http://127.0.0.1:3000'
const backend = process.env.API_URL || 'http://127.0.0.1:3000'
const headers = { 'Content-Type': 'application/json', 'X-Workspace-ID': randomUUID() }
async function call(path, body) {
  const response = await fetch(`${web}/api${path}`, { headers, ...(body ? { method: 'POST', body: JSON.stringify(body) } : {}) })
  assert.ok(response.ok, `${path}: HTTP ${response.status} ${await response.clone().text()}`)
  return response.json()
}

const html = await fetch(web).then(response => response.text())
assert.match(html, /Crypto Research AI/)
assert.equal((await call('/health')).status, 'ok')
const session = await call('/sessions', { mode: 'demo' })
const root = `/sessions/${session.id}`
const market = await call(`${root}/market`, { symbols: ['BTC'] })
assert.equal(market.latest.snapshots[0].symbol, 'BTC')
assert.match(market.latest.snapshots[0].provider, /fictional/i)
const news = await call(`${root}/chat`, { message: 'Three news articles about the same cryptocurrency' })
assert.equal(news.latest.articles[0].query, 'bitcoin')
assert.equal(news.latest.snapshots.length, 0)
const comparison = await call(`${root}/compare`, { symbols: ['BTC', 'ETH'] })
assert.deepEqual(comparison.latest.snapshots.map(item => item.symbol), ['BTC', 'ETH'])
const report = await fetch(`${web}/api${root}/reports/${comparison.turns.at(-1).id}`, { headers }).then(response => response.text())
assert.match(report, /FICTIONAL SAMPLE DATA/)
assert.ok(report.includes(comparison.turns.at(-1).reply))
const cors = await fetch(`${backend}/api/sessions`, { method: 'OPTIONS', headers: { Origin: web, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type,x-workspace-id' } })
assert.equal(cors.status, 200)
assert.equal(cors.headers.get('access-control-allow-origin'), web)
console.log('PASS: Vite → FastAPI proxy, Demo chat/memory, market, comparison, report export and CORS.')
