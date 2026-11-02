import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { ResearchPanel } from '../features/research/ResearchPanel'
import { ProviderSetup } from '../features/settings/ProviderSetup'
import { ManageInvestigation } from '../features/investigations/ManageInvestigation'
import { UnsavedChanges } from '../features/investigations/InvestigationForm'
import * as api from '../api/client'

vi.mock('../api/client', async importOriginal => ({
  ...await importOriginal<typeof api>(),
  getProviders: vi.fn(), listRuns: vi.fn(), getProgress: vi.fn(), getPlan: vi.fn(), generatePlan: vi.fn(), startResearch: vi.fn(), cancelCollection: vi.fn(),
  getGeneratedAnswer: vi.fn(), listGeneratedReports: vi.fn(), getGeneratedReport: vi.fn(), saveCredential: vi.fn(), removeCredential: vi.fn(), grantConsent: vi.fn(), revokeConsent: vi.fn(),
  setSensitive: vi.fn(), setArchived: vi.fn(), deleteInvestigation: vi.fn(),
}))

const HOSTILE = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=1</script>'
const budgets: api.Budgets = { max_steps: 25, max_searches: 8, max_pages: 10, max_tokens: 100000, max_minutes: 10 }
const ceilings: api.Budgets = { max_steps: 25, max_searches: 20, max_pages: 15, max_tokens: 400000, max_minutes: 20 }
const mockProviders: api.Providers = { mode: 'mock', live_network: false, fixture_collection: true, consent: true, budgets, budget_ceilings: ceilings, blockers: [], providers: [] }
const plan: api.Plan = { id: 'p', revision_no: 1, items: [{ id: 'a', sub_question: 'Step', search_query: 'q' }] }
const run = (over: Partial<api.CollectionRun>): api.CollectionRun => ({ id: 'r', status: 'running', mode: 'mock', created_at: '2026-11-02T00:00:00+00:00', plan_revision: 1, question_snapshot: 'Q', urls: [], error_code: null, scope: 'research_pipeline', ...over })
const progress = (over: Partial<api.Progress> = {}): api.Progress => ({ status: 'running', error_code: null, cancel_requested: false, mode: 'mock', scope: 'research_pipeline', budgets, narrow_reason: null, stages: [{ stage_key: 'discover', stage_revision: 1, status: 'completed', completed_at: 'now', error_code: null }], usage: { search_attempts: 2, model_attempts: 0, pages_retrieved: 1, estimated_tokens: 1200 }, ...over })

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getProviders).mockResolvedValue(mockProviders)
  vi.mocked(api.listRuns).mockResolvedValue([])
  vi.mocked(api.getPlan).mockResolvedValue(plan)
  vi.mocked(api.getProgress).mockResolvedValue(progress())
  vi.mocked(api.getGeneratedAnswer).mockResolvedValue(null)
  vi.mocked(api.listGeneratedReports).mockResolvedValue([])
  vi.mocked(api.cancelCollection).mockResolvedValue(undefined)
})

function panel(props: Partial<React.ComponentProps<typeof ResearchPanel>> = {}) {
  return render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <ResearchPanel investigationId="inv" plan={plan} sensitive={false} archived={false} onPlanGenerated={() => {}} {...props} /> }])} />)
}

it('shows limits before running and starts with the saved revision and chosen budgets', async () => {
  const user = userEvent.setup()
  panel()
  const pages = await screen.findByLabelText(/^Pages fetched/)
  expect(pages).toHaveValue(10)
  expect(pages).toHaveAttribute('max', '15')
  expect(screen.getByText(/Nothing leaves this computer/)).toBeVisible()
  await user.clear(pages); await user.type(pages, '3')
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
  expect(await screen.findByText(/SIMULATED · Running/)).toBeVisible()
  expect(screen.getByText(/Search attempts 2/)).toBeVisible()
  expect(screen.getByText(/1,200 tokens \(estimate\)/)).toBeVisible()
  vi.mocked(api.getProgress).mockResolvedValue(progress({ cancel_requested: true }))
  await user.click(screen.getByRole('button', { name: 'Cancel run' }))
  expect(api.cancelCollection).toHaveBeenCalledWith('r', 'inv')
  expect(await screen.findByText(/SIMULATED · Cancelling/)).toBeVisible()
})

it('never calls a stopped run complete, and says what happened and what was kept', async () => {
  vi.mocked(api.listRuns).mockResolvedValue([run({ status: 'budget_reached', error_code: 'page_budget' })])
  panel()
  expect(await screen.findByText(/SIMULATED · Budget reached/)).toBeVisible()
  expect(screen.getByText(/The page limit was reached\. Everything saved so far is kept\./)).toBeVisible()
  expect(screen.queryByText(/Completed/)).not.toBeInTheDocument()
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
  panel()
  expect(await screen.findByText(/SIMULATED · Not real research/)).toBeVisible()
  expect(screen.getByText('Cited')).toBeVisible()
  expect(screen.getByText('Not established')).toBeVisible()
  expect(screen.getAllByText('2 citation(s) failed validation and were suppressed.')).toHaveLength(2)
  expect(document.querySelector('img, script:not([src])')).toBeNull()
  const article = await screen.findByRole('article', { name: 'Research report version 1' })
  expect(within(article).getByRole('link', { name: 'Download report (.md)' })).toHaveAttribute('href', '/api/investigations/inv/generated-reports/1/download')
  await user.click(screen.getByRole('button', { name: 'Open evidence P-0001' }))
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText(/doesn’t show that the source supports the claim/)).toBeVisible()
  expect(dialog.querySelector('img')).toBeNull()
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
