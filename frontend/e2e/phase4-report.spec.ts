import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('evidence review, cited draft and immutable report export stay local and traceable', async ({ page, context, browser }) => {
  test.setTimeout(120000)
  console.log(`Phase 4 browser: Microsoft Edge ${browser.version()}`)
  const external: string[] = []
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await context.route('**/*', route => {
    if (new URL(route.request().url()).hostname !== '127.0.0.1') { external.push(route.request().url()); return route.abort() }
    return route.continue()
  })
  await page.goto('/new')
  await page.getByLabel(/^Title/).fill('Report browser study')
  await page.getByLabel(/^Main research question/).fill('Can a report keep exact citations?')
  await page.getByRole('button', { name: 'Create investigation' }).click()
  await page.getByRole('navigation', { name: 'Investigation sections' }).getByRole('link', { name: 'Evidence' }).click()
  await expect(page.getByRole('heading', { name: 'Collection and saved URLs' })).toBeVisible()

  // A saved URL is a lead only: it is never fetched and is labelled as not retrieved.
  await page.getByLabel(/^URL/).fill('https://example.org/read-later')
  await page.getByRole('button', { name: 'Save URL for later' }).click()
  await expect(page.getByText('Saved · not retrieved')).toBeVisible()

  const consent = page.getByRole('button', { name: 'Enable synthetic collection' })
  await expect(consent.or(page.getByRole('button', { name: 'Revoke fixture permission' }))).toBeVisible()
  if (await consent.isVisible()) {
    await page.getByRole('checkbox', { name: /synthetic demonstration/ }).check()
    await consent.click()
  }
  await page.getByRole('button', { name: 'Collect synthetic evidence' }).click()
  await expect(page.getByText('SIMULATED · completed', { exact: true })).toBeVisible({ timeout: 20000 })


  const review = page.getByRole('form', { name: 'Add review for P-0001' })
  await review.getByLabel('My classification').selectOption('supports')
  await review.getByLabel(/^My note/).fill('My own judgment, not verified.')
  await review.getByRole('button', { name: 'Add review' }).click()
  await expect(page.getByRole('form', { name: 'Review: P-0001 for Can a report keep exact citations?' }).getByText('Saved · revision 1')).toBeVisible()

  await page.getByRole('navigation', { name: 'Investigation sections' }).getByRole('link', { name: 'Report' }).click()
  await expect(page.getByRole('heading', { name: 'Report', level: 2, exact: true })).toBeVisible()
  await expect(page.getByText(/Simulated evidence\./)).toBeVisible()

  await page.getByRole('button', { name: 'Add claim' }).click()
  await page.getByLabel(/^Claim text 1/).fill('The fixture passage exists.')
  await page.getByRole('button', { name: 'Add citation to claim 1' }).click()
  await page.getByLabel(/^Exact quotation/).fill('SIMULATED   EVIDENCE')
  await page.getByLabel(/^Summary/).fill('<script>window.__pwned = 1</script> user summary')
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByText('Draft saved locally · revision 1')).toBeVisible()
  await expect(page.locator('.badge-cited')).toHaveText('Cited')

  await page.getByRole('button', { name: 'Create report version' }).click()
  const preview = page.getByRole('article', { name: 'Report version 1 preview' })
  await expect(preview.getByText(/1 of 1 references valid, 1 of 1 quotations match/)).toBeVisible()
  const markdown = await preview.locator('pre').innerText()
  expect(markdown).toContain('SIMULATED EVIDENCE.')
  expect(markdown).toContain('P-0001')
  expect(markdown).toContain('\\<script\\>')

  const [download] = await Promise.all([page.waitForEvent('download'), preview.getByRole('link', { name: 'Download Markdown (.md)' }).click()])
  expect(download.suggestedFilename()).toMatch(/^deeptrace-report-[0-9a-f]{8}-v1\.md$/)
  const bytes = await readFile(await download.path())
  const shown = await preview.locator('.mono').innerText()
  expect(shown).toContain(createHash('sha256').update(bytes).digest('hex'))

  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect((await new AxeBuilder({ page }).analyze()).violations.filter(v => ['serious', 'critical'].includes(v.impact ?? ''))).toEqual([])
    await page.screenshot({ path: `test-results/report-${width}.png`, fullPage: true })
  }

  await page.reload()
  await expect(page.getByLabel(/^Claim text 1/)).toHaveValue('The fixture passage exists.')
  await expect(page.getByRole('article', { name: 'Report version 1 preview' })).toBeVisible()
  await page.getByRole('button', { name: 'Open passage P-0001' }).click()
  await expect(page.getByRole('dialog').getByText(/does not show that the source supports/)).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined()
  expect(external).toEqual([])
  expect(errors).toEqual([])
})
