import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const styles = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'styles.css'), 'utf8')

function luminance(hex: string) {
  const channels = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
  return channels.reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0)
}

it('maintains readable text, actions and source indicators in both palettes', () => {
  const palettes = [...styles.matchAll(/:root(?:\[data-theme="dark"\])?\s*\{([\s\S]*?)\}/g)].slice(0, 2)
  expect(palettes).toHaveLength(2)
  for (const palette of palettes) {
    const tokens = Object.fromEntries([...palette[1].matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})/gi)].map(match => [match[1], match[2]]))
    for (const [foreground, background] of [['ink', 'surface'], ['muted', 'page'], ['muted', 'surface'], ['accent', 'accent-soft'], ['action-ink', 'accent'], ['positive', 'surface'], ['negative', 'surface']]) {
      const [low, high] = [luminance(tokens[foreground]), luminance(tokens[background])].sort((a, b) => a - b)
      expect((high + .05) / (low + .05), `${foreground} on ${background}`).toBeGreaterThanOrEqual(4.5)
    }
  }
})
