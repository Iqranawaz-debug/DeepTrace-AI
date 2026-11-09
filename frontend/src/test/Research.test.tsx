import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { renderWorkspace } from './workspace'
import { ProviderSetup } from '../features/settings/ProviderSetup'
import { ManageInvestigation } from '../features/investigations/ManageInvestigation'
import { UnsavedChanges } from '../features/investigations/InvestigationForm'
import * as api from '../api/client'

vi.mock('../api/client', async importOriginal => ({
  ...await importOriginal<typeof api>(),
  getProviders: vi.fn(), listRuns: vi.fn(), getProgress: vi.fn(), getPlan: vi.fn(), generatePlan: vi.fn(), startResearch: vi.fn(), cancelCollection: vi.fn(),
  getGeneratedAnswer: vi.fn(), listGeneratedReports: vi.fn(), getGeneratedReport: vi.fn(), saveCredential: vi.fn(), removeCredential: vi.fn(), grantConsent: vi.fn(), revokeConsent: vi.fn(),
  getInvestigation: vi.fn(), listEvidencePassages: vi.fn(), getAnswer: vi.fn(), listReports: vi.fn(), listNotes: vi.fn(),
  setSensitive: vi.fn(), setArchived: vi.fn(), deleteInvestigation: vi.fn(), getRunEvents: vi.fn(), getStorage: vi.fn(),
}))

const HOSTILE = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=1</script>'
const budgets: api.Budgets = { max_steps: 25, max_searches: 8, max_pages: 10, max_tokens: 100000, max_minutes: 10 }
const ceilings: api.Budgets = { max_steps: 25, max_searches: 20, max_pages: 15, max_tokens: 400000, max_minutes: 20 }
const mockProviders: api.Providers = { mode: 'mock', live_network: false, fixture_collection: true, consent: true, budgets, budget_ceilings: ceilings, blockers: [], providers: [] }
const plan: api.Plan = { id: 'p', revision_no: 1, items: [{ id: 'a', sub_question: 'Step', search_query: 'q' }] }
const run = (over: Partial<api.CollectionRun>): api.CollectionRun => ({ id: 'r', status: 'running', mode: 'mock', created_at: '2026-11-02T00:00:00+00:00', plan_revision: 1, question_snapshot: 'Q', urls: [], error_code: null, scope: 'research_pipeline', ...over })
const progress = (over: Partial<api.Progress> = {}): api.Progress => ({ status: 'running', error_code: null, cancel_requested: false, mode: 'mock', scope: 'research_pipeline', budgets, narrow_reason: null, queries: [{ query_text: 'first query', status: 'completed', searched_at: '2026-11-02T00:00:01+00:00', results_count: 2 }], stages: [{ stage_key: 'discover', stage_revision: 1, status: 'completed', completed_at: 'now', error_code: null }], usage: { search_attempts: 2, model_attempts: 0, pages_retrieved: 1, pages_attempted: 3, estimated_tokens: 1200 }, ...over })

const investigationOf = (over: Partial<api.Investigation> = {}): api.Investigation => ({ id: 'inv', title: 'Study', question: 'Does fixture text exist?', description: null, status: 'draft', created_at: '2026-11-02T00:00:00+00:00', updated_at: '2026-11-02T00:00:00+00:00', ...over })

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getProviders).mockResolvedValue(mockProviders)
  vi.mocked(api.listRuns).mockResolvedValue([])
  vi.mocked(api.getPlan).mockResolvedValue(plan)
  vi.mocked(api.getProgress).mockResolvedValue(progress())
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(null)
  vi.mocked(api.listGeneratedReports).mockResolvedValue([])
  vi.mocked(api.cancelCollection).mockResolvedValue(undefined)
  vi.mocked(api.getRunEvents).mockResolvedValue([])
  vi.mocked(api.getInvestigation).mockResolvedValue(investigationOf())
  vi.mocked(api.listEvidencePassages).mockResolvedValue([])
  vi.mocked(api.listNotes).mockResolvedValue([])
  vi.mocked(api.listReports).mockResolvedValue([])
  vi.mocked(api.getAnswer).mockResolvedValue({ id: null, revision_no: 0, authorship: 'user', mode: 'mock', updated_at: null, claims: [], scope_text: null, methodology_text: null, summary_text: null, limitations_text: null, next_steps_text: null })
  vi.mocked(api.getStorage).mockResolvedValue({ bytes: 1500000, warning_bytes: 500000000, over_warning: false })
})

function panel({ sensitive = false, plan: saved, path }: { sensitive?: boolean; plan?: api.Plan; path?: string } = {}) {
  vi.mocked(api.getInvestigation).mockResolvedValue(investigationOf({ sensitive }))
  if (saved) vi.mocked(api.getPlan).mockResolvedValue(saved)
  return renderWorkspace(path)
}
const findings = '/investigations/inv/findings'
const inspector = () => screen.findByRole('complementary', { name: /^Evidence( P-\d+)?$/ })

it('shows limits before running and starts with the saved revision and chosen budgets', async () => {
  const user = userEvent.setup()
  panel()
  await user.click(await screen.findByRole('button', { name: 'Run settings' }))
  const pages = await screen.findByLabelText(/^Pages fetched/)
  expect(pages).toHaveValue(10)
  expect(pages).toHaveAttribute('max', '15')
  expect(screen.getByText(/Nothing leaves this computer/)).toBeVisible()
  await user.clear(pages); await user.type(pages, '3')
  await user.click(screen.getByRole('button', { name: 'Done' }))
  await user.click(screen.getByRole('button', { name: 'Start research' }))
  await waitFor(() => expect(api.startResearch).toHaveBeenCalled())
  const [investigation, key, revision, chosen] = vi.mocked(api.startResearch).mock.calls[0]
  expect([investigation, typeof key, revision, chosen.max_pages]).toEqual(['inv', 'string', 1, 3])
})

it('requires explicit confirmation before replacing a saved plan', async () => {
  const user = userEvent.setup()
  panel()
  const generate = await screen.findByRole('button', { name: 'Generate plan' })
  expect(generate).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /Replace my saved plan/ }))
  await user.click(generate)
  await waitFor(() => expect(api.generatePlan).toHaveBeenCalledWith('inv', expect.any(String), 1, true))
})

it('explains every blocked state instead of offering a dead start button', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, consent: false })
  const { unmount } = panel()
  expect(await screen.findByText(/Enable synthetic collection/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled()
  unmount()
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, mode: 'live_free', live_network: true, fixture_collection: false, blockers: ['Add a Web search API key.'] })
  panel()
  expect(await screen.findByText(/Add a Web search API key/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled()
  expect(screen.getByRole('link', { name: 'Open setup' })).toBeVisible()
})

it('blocks hosted planning for a sensitive investigation in live mode', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, mode: 'live_free', live_network: true, fixture_collection: false })
  panel({ sensitive: true, plan: { id: null, revision_no: 0, items: [] } })
  expect(await screen.findByText(/a hosted model cannot be used/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Generate plan' })).toBeDisabled()
})

it('shows live progress, says Cancelling until persisted, and marks simulated runs', async () => {
  const user = userEvent.setup()
  vi.mocked(api.listRuns).mockResolvedValue([run({})])
  panel()
  expect((await screen.findAllByText(/SIMULATED · Running/))[0]).toBeVisible()
  expect(screen.getByText(/2 searches/)).toBeVisible()
  expect(screen.getByText(/~1,200 tokens/)).toBeVisible()
  vi.mocked(api.getProgress).mockResolvedValue(progress({ cancel_requested: true }))
  await user.click(screen.getByRole('button', { name: 'Cancel' }))
  const dialog = await screen.findByRole('dialog', { name: 'Cancel this run?' })
  expect(within(dialog).getByText('Evidence collected so far is kept.')).toBeVisible()
  expect(within(dialog).getByRole('button', { name: 'Keep running' })).toHaveFocus()
  expect(api.cancelCollection).not.toHaveBeenCalled()
  await user.click(within(dialog).getByRole('button', { name: 'Cancel run' }))
  expect(api.cancelCollection).toHaveBeenCalledWith('r', 'inv')
  expect((await screen.findAllByText(/SIMULATED · Cancelling/))[0]).toBeVisible()
})

it('never calls a stopped run complete, and says what happened and what was kept', async () => {
  vi.mocked(api.listRuns).mockResolvedValue([run({ status: 'budget_reached', error_code: 'page_budget' })])
  vi.mocked(api.getProgress).mockResolvedValue(progress({ status: 'budget_reached', error_code: 'page_budget' }))
  panel()
  expect((await screen.findAllByText(/SIMULATED · Budget reached/))[0]).toBeVisible()
  expect(screen.getByText(/The page limit was reached\. Partial results are shown and may be incomplete\./)).toBeVisible()
  expect(screen.queryByText(/Research completed/)).not.toBeInTheDocument()
  expect(screen.getByRole('list', { name: 'Research progress' })).toHaveTextContent('ReadBudget reached')
})

it('renders hostile model and source text inertly with honest evidence labels', async () => {
  const user = userEvent.setup()
  const citation: api.GeneratedCitation = { passage_id: 'p1', display_id: 'P-0001', source_id: 's', source_title: HOSTILE, original_url: 'https://fixture.example/a', fetched_at: 'now', quoted_text: null, start_offset: 0, end_offset: 5, passage_text: HOSTILE, reference_valid: true, quote_valid: null, invalid_reason: null }
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue({ run_id: 'r', provider_id: 'mock_llm', model_id: 'm', prompt_version: 'synthesize-v1', generated_at: 'now', mode: 'mock', status: 'partial', summary_text: HOSTILE, limitations_text: null, needed_evidence_text: 'More sources', suppressed_citations: 2, claims: [
    { ordinal: 1, claim_text: HOSTILE, evidence_state: 'cited', explanation: null, citations: [citation] },
    { ordinal: 2, claim_text: 'Unbacked', evidence_state: 'not_established', explanation: '2 citation(s) failed validation and were suppressed.', citations: [] },
  ] })
  const summary: api.GeneratedReportSummary = { version_no: 1, run_id: 'r', created_at: '2026-11-02T00:00:00+00:00', markdown_sha256: 'a'.repeat(64), mode: 'mock', prompt_version: 'synthesize-v1', report_schema_version: 'generated-report-v1', validation_summary: { citations: 1, quotations_matched: 0, claims_not_established: 1 } }
  vi.mocked(api.listGeneratedReports).mockResolvedValue([summary])
  vi.mocked(api.getGeneratedReport).mockResolvedValue({ ...summary, markdown_text: `# Title\n${HOSTILE}`, current_warnings: [] })
  const first = panel({ path: findings })
  expect(await screen.findByText(/SIMULATED · Not real research/)).toBeVisible()
  expect(screen.getByText('Cited')).toBeVisible()
  expect(screen.getByText('Not established')).toBeVisible()
  expect(screen.getAllByText('2 citation(s) failed validation and were suppressed.')).toHaveLength(2)
  expect(document.querySelector('img, script:not([src])')).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Open evidence P-0001' }))
  const dialog = await inspector()
  expect(within(dialog).getByText(/doesn't show that the source supports the claim/)).toBeVisible()
  expect(within(dialog).getByText(/They don't confirm the claim is true\./)).toBeVisible()
  expect(dialog.querySelector('img')).toBeNull()
  first.unmount()
  panel({ path: '/investigations/inv/report' })
  const article = await screen.findByRole('article', { name: 'Research report version 1' })
  expect(within(article).getByRole('link', { name: 'Download report (.md)' })).toHaveAttribute('href', '/api/investigations/inv/generated-reports/1/download')
  expect(document.querySelector('img, script:not([src])')).toBeNull()
  expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined()
})

const tavily: api.ProviderInfo = { id: 'tavily', role: 'Web search', data_sent: 'Your search queries.', notice: 'Queries leave this computer.', needs_credential: true, credential_state: 'Not configured', consent: false, disclosure_version: 'tavily-live-v1' }

it('keeps keys write-only and needs an explicit disclosure tick', async () => {
  const user = userEvent.setup()
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, providers: [tavily] })
  render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <ProviderSetup /> }])} />)
  const key = await screen.findByLabelText(/Web search API key/)
  expect(key).toHaveAttribute('type', 'password')
  expect(screen.getByText(/set/)).toBeVisible()
  await user.type(key, 'synthetic-key-123')
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, providers: [{ ...tavily, credential_state: 'Saved' }] })
  await user.click(screen.getByRole('button', { name: 'Save key' }))
  await waitFor(() => expect(api.saveCredential).toHaveBeenCalledWith('tavily', 'synthetic-key-123'))
  expect(await screen.findByText(/It will not be shown again/)).toBeVisible()
  expect(screen.getByLabelText(/Web search API key/)).toHaveValue('')
  expect(document.body.textContent).not.toContain('synthetic-key-123')
  const accept = screen.getByRole('button', { name: 'Accept disclosure' })
  expect(accept).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /free tier/ }))
  await user.click(accept)
  await waitFor(() => expect(api.grantConsent).toHaveBeenCalledWith('tavily', 'tavily-live-v1'))
})

it('deletes only after the exact title is typed', async () => {
  const user = userEvent.setup()
  const investigation: api.Investigation = { id: 'inv', title: 'My study', question: 'A question here', description: null, status: 'draft', created_at: 'now', updated_at: 'now', lifecycle: 'Completed' }
  render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <UnsavedChanges><ManageInvestigation investigation={investigation} onChanged={() => {}} /></UnsavedChanges> }])} />)
  expect(screen.getByText('Completed')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Delete investigation' }))
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText(/can’t be undone/)).toBeVisible()
  expect(within(dialog).getByText(/upgrade backups/)).toBeVisible()
  const confirm = within(dialog).getByRole('button', { name: 'Delete permanently' })
  expect(confirm).toBeDisabled()
  await user.type(within(dialog).getByLabelText(/Type the title/), 'My stud')
  expect(confirm).toBeDisabled()
  await user.type(within(dialog).getByLabelText(/Type the title/), 'y')
  await user.click(confirm)
  await waitFor(() => expect(api.deleteInvestigation).toHaveBeenCalledWith('inv', 'My study'))
})

const citationOf = (over: Partial<api.GeneratedCitation> = {}): api.GeneratedCitation => ({ passage_id: 'p1', display_id: 'P-0001', source_id: 's', source_title: 'Source one', source_status: 'fetched', original_url: 'https://example.org/page', fetched_at: 'now', quoted_text: 'exact   words', start_offset: 0, end_offset: 20, passage_text: 'Some exact words here.', reference_valid: true, quote_valid: true, invalid_reason: null, ...over })
const answerWith = (claims: api.GeneratedClaim[]): api.GeneratedAnswer => ({ run_id: 'r', provider_id: 'gemini', model_id: 'm', prompt_version: 'synthesize-v1', generated_at: 'now', mode: 'live_free', status: 'validated', summary_text: 'Summary', limitations_text: null, needed_evidence_text: null, suppressed_citations: 0, claims })
const claimWith = (ordinal: number, citations: api.GeneratedCitation[]): api.GeneratedClaim => ({ ordinal, claim_text: `Claim ${ordinal}`, evidence_state: 'cited', explanation: null, citations })

it('highlights the exact excerpt, links the original safely and shows the three checks', async () => {
  const user = userEvent.setup()
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(answerWith([claimWith(1, [citationOf()])]))
  panel({ path: findings })
  await user.click(await screen.findByRole('button', { name: 'Open evidence P-0001' }))
  const dialog = await inspector()
  expect(within(dialog).getByRole('heading', { name: 'Evidence P-0001' })).toHaveFocus()
  expect(dialog.querySelector('mark')?.textContent).toBe('exact words')
  const link = within(dialog).getByRole('link', { name: /Open original/ })
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(link).toHaveAttribute('target', '_blank')
  expect(link).toHaveTextContent('(opens in a new tab)')
  expect(within(dialog).getByText('example.org')).toBeVisible()
  for (const check of ['Passage found in saved sources', 'Belongs to this investigation', 'Quotation matches saved text']) expect(within(dialog).getByText(check)).toBeVisible()
  await user.keyboard('{Escape}')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Open evidence P-0001' })).toHaveFocus())
})

it('never guesses a highlight and withholds evidence for an invalid reference', async () => {
  const user = userEvent.setup()
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(answerWith([claimWith(1, [citationOf({ quoted_text: 'not in passage' }), citationOf({ passage_id: 'p2', display_id: 'P-0002', reference_valid: false, invalid_reason: 'passage_changed', passage_text: 'SECRET CHANGED TEXT', quoted_text: null, quote_valid: null })])]))
  panel({ path: findings })
  await user.click(await screen.findByRole('button', { name: 'Open evidence P-0001' }))
  const dialog = await inspector()
  expect(dialog.querySelector('mark')).toBeNull()
  expect(within(dialog).getByText("The exact excerpt couldn't be located. The full passage is shown.")).toBeVisible()
  await user.click(within(dialog).getByRole('button', { name: /Next citation/ }))
  expect(await within(dialog).findByText("This reference couldn't be confirmed, so it isn't shown as evidence.")).toBeVisible()
  expect(dialog.textContent).not.toContain('SECRET CHANGED TEXT')
  expect(within(dialog).getByText('No quotation presented')).toBeVisible()
  expect(within(dialog).getByRole('button', { name: /Previous citation/ })).toBeEnabled()
})

it('opens evidence from a ?evidence= link, explains a missing passage, and lists what cites it', async () => {
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(answerWith([claimWith(1, [citationOf()]), claimWith(2, [citationOf()])]))
  const first = panel({ path: `${findings}?evidence=p1` })
  const dialog = await inspector()
  expect(await within(dialog).findByRole('heading', { name: 'Evidence P-0001' })).toHaveFocus()
  expect(within(dialog).getByRole('button', { name: 'Finding 1: Claim 1' })).toBeVisible()
  expect(within(dialog).getByRole('button', { name: 'Finding 2: Claim 2' })).toBeVisible()
  first.unmount()
  panel({ path: `${findings}?evidence=gone` })
  expect(await within(await inspector()).findByText("This passage isn't available in this investigation.")).toBeVisible()
})

it('shows five phases with real counts and a reverse-chronological activity log', async () => {
  const user = userEvent.setup()
  vi.mocked(api.listRuns).mockResolvedValue([run({})])
  vi.mocked(api.getRunEvents).mockResolvedValue([{ id: 'e1', event_type: 'source_saved', created_at: '2026-11-02T00:00:05+00:00' }, { id: 'e2', event_type: 'running', created_at: '2026-11-02T00:00:00+00:00' }])
  panel()
  const tracker = await screen.findByRole('list', { name: 'Research progress' })
  const phases = within(tracker).getAllByRole('listitem')
  expect(phases.map(item => item.textContent)).toEqual(['PlanCompleted', 'DiscoverCompleted', 'ReadIn progress', 'CheckPending', 'ReportPending'])
  expect(phases[2]).toHaveAttribute('aria-current', 'step')
  expect(screen.getByText('Reading sources (3 of 10 pages)')).toBeVisible()
  await user.click(screen.getByText('Activity'))
  const log = await screen.findByText('Source saved')
  const items = within(log.closest('ol') as HTMLElement).getAllByRole('listitem').map(item => item.textContent ?? '')
  expect(items[0]).toContain('Source saved')
  expect(items[1]).toContain('Searched: first query (2 results)')
  expect(items[2]).toContain('Run started')
})

it('shows saved size and warns only over the threshold', async () => {
  const investigation: api.Investigation = { id: 'inv', title: 'T', question: 'A question here', description: null, status: 'draft', created_at: 'now', updated_at: 'now' }
  const tree = <RouterProvider router={createMemoryRouter([{ path: '*', element: <UnsavedChanges><ManageInvestigation investigation={investigation} onChanged={() => {}} /></UnsavedChanges> }])} />
  const first = render(tree)
  expect(await screen.findByText('Saved text: 1.5 MB')).toBeVisible()
  expect(screen.queryByText(/Consider deleting/)).not.toBeInTheDocument()
  first.unmount()
  vi.mocked(api.getStorage).mockResolvedValue({ bytes: 600000000, warning_bytes: 500000000, over_warning: true })
  render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <UnsavedChanges><ManageInvestigation investigation={investigation} onChanged={() => {}} /></UnsavedChanges> }])} />)
  expect(await screen.findByText(/stores over 500 MB of text/)).toBeVisible()
})

it('explains a blocked save during an active run instead of reporting a conflict', () => {
  const blocked = new api.ApiError(409, 'Wait for collection to finish before editing.', 'run_active')
  expect(blocked.message).toBe('A run is in progress. Wait for it to finish, then save again. Your edits are still here.')
  expect(blocked.message).not.toContain('Newer changes exist')
  expect(new api.ApiError(409, 'Newer plan changes exist.', 'conflict').message).toContain('Newer changes exist')
})

it('shows one clear message while Gemini drafts a plan, not contradictory hints', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ ...mockProviders, mode: 'live_free', live_network: true, fixture_collection: false })
  vi.mocked(api.listRuns).mockResolvedValue([run({ scope: 'plan_generation', mode: 'live_free' })])
  vi.mocked(api.getProgress).mockResolvedValue(progress({ scope: 'plan_generation', stages: [] }))
  panel({ plan: { id: null, revision_no: 0, items: [] } })
  expect(await screen.findByText(/Gemini is drafting your plan\. This can take up to 2½ minutes\./)).toBeVisible()
  expect(screen.queryByText('A run is already active.')).not.toBeInTheDocument()
  expect(screen.queryByText('Add at least one plan step first.')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Generate plan' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled()
})

it('re-reads the investigation when a run finishes so its status label updates', async () => {
  vi.mocked(api.listRuns).mockResolvedValue([run({})])
  panel()
  expect((await screen.findAllByText(/SIMULATED · Running/))[0]).toBeVisible()
  expect(api.getInvestigation).toHaveBeenCalledTimes(1)
  vi.mocked(api.listRuns).mockResolvedValue([run({ status: 'completed' })])
  vi.mocked(api.getProgress).mockResolvedValue(progress({ status: 'completed' }))
  await waitFor(() => expect(api.getInvestigation).toHaveBeenCalledTimes(2), { timeout: 5000 })
})

it('shows a model failure after reading on Check, with the real reason beside the tracker', async () => {
  const stages = ['discover', 'fetch', 'rank'].map(stage_key => ({ stage_key, stage_revision: 1, status: 'completed', completed_at: 'now', error_code: null }))
  vi.mocked(api.listRuns).mockResolvedValue([run({ status: 'failed', error_code: 'unavailable', mode: 'live_free' })])
  vi.mocked(api.getProgress).mockResolvedValue(progress({ status: 'failed', error_code: 'unavailable', stages }))
  panel()
  const tracker = await screen.findByRole('list', { name: 'Research progress' })
  expect(within(tracker).getAllByRole('listitem').map(item => item.textContent)).toEqual(['PlanCompleted', 'DiscoverCompleted', 'ReadCompleted', 'CheckFailed', 'ReportNot reached'])
  const outline = screen.getByRole('complementary', { name: 'Investigation outline' })
  expect(within(outline).getByText(/A provider didn't respond, even after retries.*Saved sources are kept\./)).toBeVisible()
})
