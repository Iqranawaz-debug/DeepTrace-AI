import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('M1 journey: plan, bounded mock research, cited answer, report, sources, delete', async ({ page, context, browser }) => {
  test.setTimeout(180000)
  console.log(`M1 browser: Microsoft Edge ${browser.version()}`)
  const external: string[] = []
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await context.route('**/*', route => {
    if (new URL(route.request().url()).hostname !== '127.0.0.1') { external.push(route.request().url()); return route.abort() }
    return route.continue()
  })
  const serious = async () => (await new AxeBuilder({ page }).analyze()).violations.filter(v => ['serious', 'critical'].includes(v.impact ?? ''))

  await page.goto('/new')
  await page.getByLabel(/^Title/).fill('M1 browser study')
  await page.getByLabel(/^Main research question/).fill('How do synthetic fixtures behave in a bounded research run?')
  await page.getByRole('button', { name: 'Create investigation' }).click()
  await expect(page.getByRole('heading', { name: 'Research', exact: true })).toBeVisible()
  await expect(page.getByText(/Nothing leaves this computer/)).toBeVisible()

  const consent = page.getByRole('button', { name: 'Enable synthetic collection' })
  await expect(consent.or(page.getByRole('button', { name: 'Revoke fixture permission' }))).toBeVisible()
  if (await consent.isVisible()) {
    await page.getByRole('checkbox', { name: /synthetic demonstration/ }).check()
    await consent.click()
  }

  // Plan: generated, then shown only when the user chooses (unsaved edits are never replaced).
  await page.getByRole('button', { name: 'Generate plan' }).click()
  await page.getByRole('button', { name: 'Show generated plan' }).click({ timeout: 30000 })
  await expect(page.getByLabel(/^Sub-question 1/)).toHaveValue(/SIMULATED/)
  await expect(page.getByLabel(/^Sub-question 3/)).toBeVisible()

  // Limits are visible and bounded before anything runs.
  await expect(page.getByLabel(/^Pages fetched/)).toHaveAttribute('max', '15')
  await page.getByRole('button', { name: 'Start research' }).click()
  await expect(page.getByText('Research completed. Review the report and the limitations.')).toBeVisible({ timeout: 60000 })
  await expect(page.getByText(/SIMULATED · Completed/)).toBeVisible()
  await expect(page.getByRole('list', { name: 'Research progress' }).getByRole('listitem')).toHaveText([/Plan.*Completed/, /Discover.*Completed/, /Read.*Completed/, /Check.*Completed/, /Report.*Completed/])
  await page.getByText('Activity', { exact: true }).click()
  await expect(page.getByText(/Searched: .*results\)/).first()).toBeVisible()
  await expect(page.getByText('Limits are ceilings, not targets.', { exact: false })).toBeVisible()

  const findings = page.getByRole('region', { name: 'Findings' })
  await expect(findings.locator('.badge-cited').first()).toHaveText('Cited')
  await expect(findings.locator('.badge-missing').first()).toHaveText('Not established')
  await findings.getByRole('button', { name: /^Open evidence P-/ }).first().click()
  const evidence = page.getByRole('dialog')
  await expect(evidence.getByText("These checks confirm the reference and wording. They don't confirm the claim is true.")).toBeVisible()
  await expect(evidence.getByText('Belongs to this investigation')).toBeVisible()
  await expect(evidence.locator('mark')).toHaveText(/SIMULATED|Fixture|Simulated/)
  expect(page.url()).toContain('evidence=')
  await expect(evidence.getByRole('link', { name: /Open original/ })).toHaveAttribute('rel', 'noopener noreferrer')
  // A refresh restores the open evidence, and Back closes it before leaving the page.
  await page.reload()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('dialog').getByRole('heading', { name: /^Evidence P-/ })).toBeFocused()
  expect(await serious()).toEqual([])
  await page.keyboard.press('Escape')
  await expect(evidence).not.toBeVisible()
  expect(page.url()).not.toContain('evidence=')

  const article = page.getByRole('article', { name: 'Research report version 1' })
  const markdown = await article.locator('pre').innerText()
  for (const expected of ['AI-generated research aid. Verify important findings using original sources.', 'SIMULATED RESEARCH', '## Findings', '## Supporting Evidence', '## Conflicting or Missing Evidence', '## Limitations', '## Methodology', '## References', 'synthesize-v2']) expect(markdown).toContain(expected)
  const [download] = await Promise.all([page.waitForEvent('download'), article.getByRole('link', { name: 'Download report (.md)' }).click()])
  expect(download.suggestedFilename()).toMatch(/^deeptrace-research-[0-9a-f]{8}-v1\.md$/)
  const bytes = await readFile(await download.path())
  expect(await article.locator('.hash').innerText()).toContain(createHash('sha256').update(bytes).digest('hex'))
  expect(bytes.toString('utf-8')).toContain('## References')

  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(await serious()).toEqual([])
    await page.screenshot({ path: `test-results/m1-workspace-${width}.png`, fullPage: true })
  }

  // Restart-free persistence through reload.
  await page.reload()
  await expect(page.getByText(/SIMULATED · Completed/)).toBeVisible()
  await expect(page.getByRole('article', { name: 'Research report version 1' })).toBeVisible()

  // Sources show honest statuses, including what could not be read.
  await page.getByRole('navigation', { name: 'Investigation' }).getByRole('link', { name: 'Sources' }).click()
  await expect(page.getByRole('heading', { name: 'Sources', level: 1 })).toBeFocused()
  await expect(page.getByText(/\d+ fetched/)).toBeVisible()
  await page.getByRole('button', { name: /^Show details/ }).first().click()
  await expect(page.getByText('Author', { exact: true })).toBeVisible()
  await expect(page.getByText('Unknown').first()).toBeVisible()
  expect(await serious()).toEqual([])

  // The Report tab also reaches the saved generated report.
  await page.getByRole('navigation', { name: 'Investigation' }).getByRole('link', { name: 'Report' }).click()
  await expect(page.getByRole('article', { name: 'Research report version 1' })).toBeVisible()

  // Dashboard reflects real state.
  await page.goto('/')
  const card = page.getByRole('listitem').filter({ hasText: 'M1 browser study' })
  await expect(card.getByText('Completed', { exact: true })).toBeVisible()
  await expect(card.getByText(/[1-9]\d* source\(s\)/)).toBeVisible()
  await card.getByRole('link', { name: 'M1 browser study', exact: true }).click()

  // Archive blocks new work; unarchive restores it.
  await expect(page.getByText(/Saved text: .* MB/)).toBeVisible()
  await page.getByRole('button', { name: 'Archive' }).click()
  await expect(page.getByText('This investigation is archived.')).toBeVisible({ timeout: 10000 })
  await expect(page.getByRole('button', { name: 'Start research' })).toBeDisabled()
  await page.getByRole('button', { name: 'Unarchive' }).click()
  await expect(page.getByRole('button', { name: 'Start research' })).toBeEnabled({ timeout: 10000 })

  // Setup shows honest provider state in mock mode, without any key.
  await page.goto('/setup')
  await expect(page.getByRole('heading', { name: 'Set up research' })).toBeVisible()
  await expect(page.getByText(/A web page can never switch this on/)).toBeVisible()
  await expect(page.getByLabel('Web search API key')).toHaveAttribute('type', 'password')
  expect(await serious()).toEqual([])
  await page.goBack()

  // Delete needs the exact title and returns to a dashboard without it.
  await page.getByRole('button', { name: 'Delete investigation' }).click()
  const confirm = page.getByRole('button', { name: 'Delete permanently' })
  await expect(confirm).toBeDisabled()
  await page.getByLabel(/Type the title/).fill('M1 browser study')
  await confirm.click()
  await expect(page.getByRole('heading', { name: 'Investigations' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'M1 browser study' })).toHaveCount(0)

  expect(external).toEqual([])
  expect(errors).toEqual([])
})
