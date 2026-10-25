import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('responsive shell, local-only assets, accessibility and navigation', async ({ page }) => {
  const external: string[] = []
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/*', route => {
    if (new URL(route.request().url()).hostname !== '127.0.0.1') {
      external.push(route.request().url())
      return route.abort()
    }
    return route.continue()
  })
  for (const width of [360, 390, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await expect(page.getByText('Local backend connected')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'No investigations yet' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(results.violations.filter(v => ['critical', 'serious'].includes(v.impact ?? ''))).toEqual([])
    if (width === 1440) await page.screenshot({ path: 'test-results/dashboard-desktop.png', fullPage: true })
    if (width === 390) await page.screenshot({ path: 'test-results/dashboard-mobile.png', fullPage: true })
  }
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeFocused()
  expect((await new AxeBuilder({ page }).analyze()).violations.filter(v => ['critical', 'serious'].includes(v.impact ?? ''))).toEqual([])
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
  await page.emulateMedia({ reducedMotion: 'reduce', forcedColors: 'active' })
  await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible()
  expect(external).toEqual([])
  expect(errors).toEqual([])
})

test('connection failure and retry remain honest', async ({ page }) => {
  await page.route('**/api/health', route => route.abort())
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('Local backend unavailable')
  await page.unroute('**/api/health')
  await page.getByRole('button', { name: 'Retry connection' }).click()
  await expect(page.getByText('Local backend connected')).toBeVisible()
})
