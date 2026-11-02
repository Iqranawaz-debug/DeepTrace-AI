import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('synthetic evidence persists with provenance, accessible inspector and no external traffic', async ({ page, context, browser }) => {
  test.setTimeout(90000)
  console.log(`Phase 3 browser: Microsoft Edge ${browser.version()}`)
  const external: string[] = []
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await context.route('**/*', route => {
    if (new URL(route.request().url()).hostname !== '127.0.0.1') { external.push(route.request().url()); return route.abort() }
    return route.continue()
  })
  await page.goto('/new')
  await page.getByLabel(/^Title/).fill('Synthetic evidence browser study')
  await page.getByLabel(/^Main research question/).fill('Can synthetic sources retain exact provenance?')
  await page.getByRole('button', { name: 'Create investigation' }).click()
  await expect(page.getByRole('heading', { name: 'Evidence workspace' })).toBeVisible()
  const consent = page.getByRole('button', { name: 'Enable synthetic collection' })
  // Wait for the provider state to load; isVisible() alone does not wait and races the poll.
  await expect(consent.or(page.getByRole('button', { name: 'Revoke fixture permission' }))).toBeVisible()
  if (await consent.isVisible()) {
    await page.getByRole('checkbox', { name: /synthetic demonstration/ }).check()
    await consent.click()
  }
  await page.getByRole('button', { name: 'Collect synthetic evidence' }).click()
  await expect(page.getByText('SIMULATED · completed', { exact: true })).toBeVisible({ timeout: 15000 })
  await page.getByRole('button', { name: 'Inspect source' }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('P-0001', { exact: true })).toBeVisible()
  await expect(dialog.getByText('SHA-256 of saved text', { exact: true })).toBeVisible()
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `test-results/evidence-inspector-${width}.png`, fullPage: true })
  }
  await page.keyboard.press('Escape')
  await expect(dialog).not.toBeVisible()
  await page.reload()
  await expect(page.getByText('SIMULATED · completed', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Collect synthetic evidence' }).click()
  await expect(page.getByText(/Duplicate of saved source/)).toBeVisible({ timeout: 15000 })
  await page.getByLabel('Synthetic source URLs (one per line)').fill('https://fixture.example/failure')
  await page.getByRole('button', { name: 'Collect synthetic evidence' }).click()
  await expect(page.getByText('SIMULATED · failed', { exact: true })).toBeVisible({ timeout: 15000 })
  await page.getByRole('button', { name: 'Revoke fixture permission' }).click()
  await expect(page.getByRole('button', { name: 'Collect synthetic evidence' })).toBeDisabled()
  await page.setViewportSize({ width: 390, height: 900 })
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  expect(external).toEqual([])
  expect(errors).toEqual([])
})

