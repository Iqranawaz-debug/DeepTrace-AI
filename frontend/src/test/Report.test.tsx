import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { renderWorkspace } from './workspace'
import { SavedUrls } from '../features/evidence/SavedUrls'
import * as api from '../api/client'

vi.mock('../api/client', async importOriginal => ({
  ...await importOriginal<typeof api>(),
  getInvestigation: vi.fn(), getPlan: vi.fn(), listEvidencePassages: vi.fn(), listNotes: vi.fn(), getAnswer: vi.fn(),
  saveAnswer: vi.fn(), saveNote: vi.fn(), listReports: vi.fn(), getReport: vi.fn(), createReport: vi.fn(), listSavedUrls: vi.fn(), saveUrl: vi.fn(), getGeneratedAnswer: vi.fn(), listGeneratedReports: vi.fn(),
  getProviders: vi.fn(), listRuns: vi.fn(), getProgress: vi.fn(), listSources: vi.fn(),
}))

const HOSTILE = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=1</script>'
const passage: api.EvidencePassage = { id: 'p1', display_id: 'P-0001', source_id: 's1', source_title: HOSTILE, source_status: 'fetched', source_origin: 'mock', original_url: 'https://fixture.example/article', start_offset: 0, end_offset: 20, text: `SIMULATED EVIDENCE ${HOSTILE}`, extraction_version: 'v2' }
const empty: api.Answer = { id: null, revision_no: 0, authorship: 'user', mode: 'mock', updated_at: null, claims: [], scope_text: null, methodology_text: null, summary_text: null, limitations_text: null, next_steps_text: null }

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getInvestigation).mockResolvedValue({ id: 'inv', title: 'Study', question: 'Does fixture text exist?', description: null, status: 'draft', created_at: '2026-10-28T00:00:00+00:00', updated_at: '2026-10-28T00:00:00+00:00' })
  vi.mocked(api.getPlan).mockResolvedValue({ id: null, revision_no: 0, items: [] })
  vi.mocked(api.listEvidencePassages).mockResolvedValue([passage])
  vi.mocked(api.listNotes).mockResolvedValue([])
  vi.mocked(api.getAnswer).mockResolvedValue(empty)
  vi.mocked(api.listReports).mockResolvedValue([])
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(null)
  vi.mocked(api.listGeneratedReports).mockResolvedValue([])
  vi.mocked(api.getProviders).mockResolvedValue({ mode: 'mock', live_network: false, fixture_collection: true, consent: true, blockers: [], providers: [] })
  vi.mocked(api.listRuns).mockResolvedValue([])
  vi.mocked(api.listSources).mockResolvedValue([])
  vi.mocked(api.listSavedUrls).mockResolvedValue([])
})

function page(tab = 'report') {
  return renderWorkspace(`/investigations/inv/${tab}`)
}

it('renders hostile source text inertly and labels simulated evidence', async () => {
  const evidence = page('evidence')
  expect(await screen.findByText(`SIMULATED EVIDENCE ${HOSTILE}`)).toBeVisible()
  expect(document.querySelector('img, script:not([src])')).toBeNull()
  evidence.unmount()
  page()
  expect(await screen.findByText(/Simulated evidence\./)).toBeVisible()
  expect(document.querySelector('img, script:not([src])')).toBeNull()
  expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined()
  expect(screen.getByRole('button', { name: 'Create report version' })).toBeDisabled()
  expect(screen.getByText('Save the draft first.')).toBeVisible()
})

it('keeps edits and shows the server reason when a citation is rejected', async () => {
  const user = userEvent.setup()
  vi.mocked(api.saveAnswer).mockRejectedValue(new api.ApiError(422, 'Citations were not saved: claim 1 citation 1: quote_mismatch.'))
  page()
  await user.click(await screen.findByRole('button', { name: 'Add claim' }))
  await user.type(screen.getByLabelText(/^Claim text 1/), 'Fixture text exists.')
  await user.click(screen.getByRole('button', { name: 'Add citation to claim 1' }))
  await user.type(screen.getByLabelText(/Exact quotation/), 'not in passage')
  await user.click(screen.getByRole('button', { name: 'Save draft' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('quote_mismatch')
  expect(screen.getByLabelText(/^Claim text 1/)).toHaveValue('Fixture text exists.')
  expect(screen.getByText('Unsaved draft changes')).toBeVisible()
  const [, , claims] = vi.mocked(api.saveAnswer).mock.calls[0]
  expect(claims[0].citations).toEqual([{ passage_id: 'p1', relation: 'supports', quoted_text: 'not in passage' }])
})

it('shows saved evidence states, opens the cited passage and previews exact report bytes', async () => {
  const user = userEvent.setup()
  const citation: api.Citation = { id: 'c1', passage_id: 'p1', display_id: 'P-0001', source_id: 's1', source_title: 'Synthetic', relation: 'supports', quoted_text: 'SIMULATED EVIDENCE', reference_valid: true, quote_valid: true, invalid_reason: null, start_offset: 0, end_offset: 20, passage_text: 'SIMULATED EVIDENCE text' }
  vi.mocked(api.getAnswer).mockResolvedValue({ ...empty, id: 'a', revision_no: 1, claims: [
    { id: 'k1', ordinal: 1, claim_type: 'finding', claim_text: 'Cited claim', evidence_state: 'cited', citations: [citation] },
    { id: 'k2', ordinal: 2, claim_type: 'gap', claim_text: 'Missing', evidence_state: 'not_established', citations: [] },
  ] })
  const markdown = '# Study\n\n\\<script\\> literal'
  vi.mocked(api.listReports).mockResolvedValue([{ version_no: 1, created_at: '2026-10-28T00:00:00+00:00', answer_revision: 1, markdown_sha256: 'a'.repeat(64), mode: 'mock', report_schema_version: 'manual-report-v1', validation_summary: { citations: 1, citations_reference_valid: 1, quotations: 1, quotations_matched: 1, claims_not_established: 1 } }])
  vi.mocked(api.getReport).mockImplementation(async () => ({ ...(await api.listReports('inv'))[0], markdown_text: markdown, current_warnings: [] }))
  page()
  expect(await screen.findByText('Cited', { selector: '.badge-cited' })).toBeVisible()
  expect(screen.getByText('Not established', { selector: '.badge-missing' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Open passage P-0001' }))
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText('SIMULATED EVIDENCE text')).toBeVisible()
  expect(within(dialog).getByText(/does not show that the source supports/)).toBeVisible()
  await user.keyboard('{Escape}')
  const preview = await screen.findByRole('article', { name: 'Report version 1 preview' })
  expect(within(preview).getByText((_, node) => node?.tagName === 'PRE' && node.textContent === markdown)).toBeVisible()
  expect(within(preview).getByRole('link', { name: 'Download Markdown (.md)' })).toHaveAttribute('href', '/api/investigations/inv/reports/1/download')
  expect(within(preview).getByText(/1 claims are not established/)).toBeVisible()
})

it('labels saved URLs as not retrieved and reuses the retry identifier', async () => {
  const user = userEvent.setup()
  vi.mocked(api.listSavedUrls).mockResolvedValue([])
  vi.mocked(api.saveUrl).mockRejectedValueOnce(new api.ApiError(0)).mockImplementation(async (_inv, id, url, note) => ({ id, original_url: url, canonical_url: url, note, created_at: '2026-10-28T00:00:00+00:00', retrieved: false }))
  render(<SavedUrls investigationId="inv" />)
  expect(await screen.findByText(/does not contact these sites/)).toBeVisible()
  await user.type(screen.getByLabelText(/^URL/), 'https://example.org/read-later')
  await user.click(screen.getByRole('button', { name: 'Save URL for later' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('was not saved')
  await user.click(screen.getByRole('button', { name: 'Save URL for later' }))
  expect(await screen.findByText('Saved · not retrieved')).toBeVisible()
  await waitFor(() => expect(vi.mocked(api.saveUrl).mock.calls[0][1]).toBe(vi.mocked(api.saveUrl).mock.calls[1][1]))
})

it('reorders claims from the keyboard and saves the new order', async () => {
  const user = userEvent.setup()
  vi.mocked(api.saveAnswer).mockImplementation(async (_id, fields, claims, revision) => ({ ...empty, ...fields, id: 'a', revision_no: revision + 1, claims: claims.map((c, i) => ({ ...c, ordinal: i + 1, evidence_state: 'not_established' as const, citations: [] })) }))
  page()
  await user.click(await screen.findByRole('button', { name: 'Add claim' }))
  await user.type(screen.getByLabelText(/^Claim text 1/), 'First')
  await user.click(screen.getByRole('button', { name: 'Add claim' }))
  await user.type(screen.getByLabelText(/^Claim text 2/), 'Second')
  expect(screen.getByRole('button', { name: 'Move up claim 1' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Move down claim 2' })).toBeDisabled()
  screen.getByRole('button', { name: 'Move up claim 2' }).focus()
  await user.keyboard('{Enter}')
  expect(screen.getByText(/Moved claim to position 1 of 2/)).toBeVisible()
  expect(screen.getByLabelText(/^Claim text 1/)).toHaveValue('Second')
  await user.click(screen.getByRole('button', { name: 'Save draft' }))
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalled())
  expect(vi.mocked(api.saveAnswer).mock.calls[0][2].map(c => c.claim_text)).toEqual(['Second', 'First'])
  expect(await screen.findByText('Draft saved locally · revision 1')).toBeVisible()
})
