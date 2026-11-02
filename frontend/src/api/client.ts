export interface Health { status: 'ok' | 'ready'; version: string }

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch('/api/health', { signal, credentials: 'omit', cache: 'no-store' })
  if (!response.ok) throw new Error('Local backend unavailable')
  const data: unknown = await response.json()
  if (!data || typeof data !== 'object' || !('status' in data) || data.status !== 'ok'
    || !('version' in data) || typeof data.version !== 'string') {
    throw new Error('Unexpected health response')
  }
  return { status: 'ok', version: data.version }
}
export interface Investigation { id: string; title: string; question: string; description: string | null; status: 'draft'; created_at: string; updated_at: string; sensitive?: boolean; archived_at?: string | null; source_count?: number; lifecycle?: string }
export interface PlanItem { id: string; sub_question: string; search_query: string | null }
export interface Plan { id: string | null; revision_no: number; items: PlanItem[] }
export interface InvestigationList { items: Investigation[]; total: number }
export type Fields = Pick<Investigation, 'title' | 'question' | 'description'>

export class ApiError extends Error {
  status: number
  /** Fixed server-authored message (never echoes user content), shown alongside the generic one. */
  detail: string
  constructor(status: number, detail = '') {
    super(status === 409 ? 'Newer changes exist. Your edits are still here. Copy them before loading the latest saved version.' : status === 403 ? 'Local session expired or request denied. Your edits are still here. Retry to renew the session.' : status === 422 ? 'Check required fields and input limits. Your edits are still here.' : 'The local request failed. Your edits are still here. Check the backend and retry.')
    this.status = status
    this.detail = detail
  }
}
async function failure(response: Response): Promise<ApiError> {
  try {
    const data: unknown = await response.json()
    const message = record(data) && record(data.error) && typeof data.error.message === 'string' ? data.error.message : ''
    return new ApiError(response.status, message.slice(0, 500))
  } catch { return new ApiError(response.status) }
}
function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' }
function investigation(value: unknown): value is Investigation {
  return record(value) && ['id', 'title', 'question', 'created_at', 'updated_at'].every(key => typeof value[key] === 'string') && value.status === 'draft' && (value.description === null || typeof value.description === 'string')
}
function plan(value: unknown): value is Plan {
  return record(value) && (value.id === null || typeof value.id === 'string') && Number.isInteger(value.revision_no) && Array.isArray(value.items) && value.items.length <= 8 && value.items.every(item => record(item) && typeof item.id === 'string' && typeof item.sub_question === 'string' && (item.search_query === null || typeof item.search_query === 'string'))
}
async function request(path: string, method = 'GET', body?: unknown): Promise<unknown> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 10000)
  try {
    const headers: Record<string, string> = {}
    if (method !== 'GET') {
      // Token lives only in this request's memory; never URL or browser storage.
      const session = await fetch('/api/session', { credentials: 'omit', cache: 'no-store', signal: controller.signal })
      if (!session.ok) throw new ApiError(session.status)
      const data: unknown = await session.json()
      if (!record(data) || typeof data.token !== 'string') throw new ApiError(502)
      headers['X-DeepTrace-Token'] = data.token
      headers['Content-Type'] = 'application/json'
    }
    const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'omit', cache: 'no-store', signal: controller.signal })
    if (!response.ok) throw await failure(response)
    return await response.json()
  } catch (error) { throw error instanceof ApiError ? error : new ApiError(0) }
  finally { clearTimeout(timeout) }
}
function checked<T>(data: unknown, guard: (value: unknown) => value is T): T {
  if (!guard(data)) throw new ApiError(502)
  return data
}
export async function listInvestigations(query = '', offset = 0): Promise<InvestigationList> {
  const data = await request(`/api/investigations?q=${encodeURIComponent(query)}&limit=25&offset=${offset}`)
  if (!record(data) || !Array.isArray(data.items) || !data.items.every(investigation) || typeof data.total !== 'number') throw new ApiError(502)
  return { items: data.items, total: data.total }
}
export async function getInvestigation(id: string) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}`), investigation) }
export async function createInvestigation(id: string, fields: Fields) { return checked(await request('/api/investigations', 'POST', { id, ...fields }), investigation) }
export async function editInvestigation(id: string, fields: Fields, timestamp: string) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}`, 'PATCH', { ...fields, expected_updated_at: timestamp }), investigation) }
export async function getPlan(id: string) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}/plan`), plan) }
export async function savePlan(id: string, items: PlanItem[], revision: number) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}/plan`, 'PUT', { items, expected_revision: revision }), plan) }

export interface CollectionRun { id: string; status: string; mode: string; created_at: string; plan_revision: number; question_snapshot: string; urls: string[]; error_code: string | null; scope?: string }
export interface Source { id: string; title: string | null; original_url: string; canonical_url: string; status: string; origin: string; limitation: string | null; duplicate_of: string | null; author?: string | null; published_at?: string | null; extracted_text?: string | null; text_sha256?: string | null; extraction_version?: string | null; fetched_at: string | null; extracted_at: string | null }
export interface Passage { id: string; display_id: string; text: string; start_offset: number; end_offset: number }
export interface Budgets { max_steps: number; max_searches: number; max_pages: number; max_tokens: number; max_minutes: number }
export interface ProviderInfo { id: string; role: string; data_sent: string; notice: string; needs_credential: boolean; credential_state: string; consent: boolean; disclosure_version: string }
export interface Providers { fixture_collection: boolean; consent: boolean; live_network: boolean; mode?: string; providers?: ProviderInfo[]; llm_model?: string | null; budgets?: Budgets; budget_ceilings?: Budgets; blockers?: string[] }
const owned = (investigation: string) => `investigation_id=${encodeURIComponent(investigation)}`
function collectionRun(value: unknown): value is CollectionRun {
  return record(value) && ['id', 'status', 'mode', 'created_at', 'question_snapshot'].every(key => typeof value[key] === 'string') && Number.isInteger(value.plan_revision) && Array.isArray(value.urls) && value.urls.every(url => typeof url === 'string')
}
function source(value: unknown): value is Source {
  return record(value) && ['id', 'original_url', 'canonical_url', 'status', 'origin'].every(key => typeof value[key] === 'string') && (value.title === null || typeof value.title === 'string')
}
function passage(value: unknown): value is Passage {
  return record(value) && ['id', 'display_id', 'text'].every(key => typeof value[key] === 'string') && Number.isInteger(value.start_offset) && Number.isInteger(value.end_offset)
}
function arrayOf<T>(guard: (value: unknown) => value is T) { return (value: unknown): value is T[] => Array.isArray(value) && value.every(guard) }
export async function getProviders() {
  const value = await request('/api/providers')
  if (!record(value) || typeof value.fixture_collection !== 'boolean' || typeof value.consent !== 'boolean' || typeof value.live_network !== 'boolean') throw new ApiError(502)
  return value as unknown as Providers
}
export async function setCollectionConsent(accepted: boolean) { await request(accepted ? '/api/web-consent' : '/api/web-consent/revoke', 'POST', { accepted }) }
export async function listRuns(id: string, offset = 0) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}/runs?offset=${offset}`), arrayOf(collectionRun)) }
export async function listSources(id: string, offset = 0) { return checked(await request(`/api/investigations/${encodeURIComponent(id)}/sources?offset=${offset}`), arrayOf(source)) }
export async function startCollection(investigation: string, id: string, urls: string[], revision: number) { return checked(await request(`/api/investigations/${encodeURIComponent(investigation)}/runs`, 'POST', { id, urls, expected_revision: revision }), collectionRun) }
export async function cancelCollection(id: string, investigation: string) { await request(`/api/runs/${encodeURIComponent(id)}/cancel?${owned(investigation)}`, 'POST', {}) }
export async function getSource(id: string, investigation: string) { return checked(await request(`/api/sources/${encodeURIComponent(id)}?${owned(investigation)}`), source) }
export async function getPassages(id: string, investigation: string, offset = 0) { return checked(await request(`/api/sources/${encodeURIComponent(id)}/passages?${owned(investigation)}&offset=${offset}`), arrayOf(passage)) }

// Phase 4: saved URLs (never retrieved), evidence review, user-authored drafts, immutable reports.
export interface SavedUrl { id: string; original_url: string; canonical_url: string; note: string | null; created_at: string; retrieved: false }
export interface EvidencePassage { id: string; display_id: string; source_id: string; source_title: string | null; source_status: string; source_origin: string; original_url: string; start_offset: number; end_offset: number; text: string; extraction_version: string }
export type Stance = 'unreviewed' | 'supports' | 'contradicts' | 'context' | 'insufficient'
export type Relation = 'supports' | 'contradicts' | 'context'
export type ClaimType = 'finding' | 'interpretation' | 'conflict' | 'hypothesis' | 'gap' | 'conclusion'
export interface EvidenceNote { id: string; passage_id: string; display_id: string; source_id: string; source_title: string | null; target_key: string; target_label: string; target_current: boolean; stance: Stance; note: string | null; revision_no: number; created_at: string; updated_at: string }
export interface CitationDraft { passage_id: string; relation: Relation; quoted_text: string | null }
export interface Citation extends CitationDraft { id: string; display_id: string; source_id: string; source_title: string | null; reference_valid: boolean; quote_valid: boolean | null; invalid_reason: string | null; start_offset: number; end_offset: number; passage_text: string }
export interface Claim { id: string; ordinal: number; claim_type: ClaimType; claim_text: string; evidence_state: 'cited' | 'not_established'; citations: Citation[] }
export const ANSWER_FIELDS = ['scope_text', 'methodology_text', 'summary_text', 'limitations_text', 'next_steps_text'] as const
export type AnswerField = typeof ANSWER_FIELDS[number]
export type Answer = { id: string | null; revision_no: number; authorship: 'user'; mode: string; updated_at: string | null; claims: Claim[] } & Record<AnswerField, string | null>
export interface ClaimDraft { id: string; claim_type: ClaimType; claim_text: string; citations: CitationDraft[] }
export interface ReportSummary { version_no: number; created_at: string; answer_revision: number; markdown_sha256: string; mode: string; report_schema_version: string; validation_summary: Record<string, number> }
export interface ReportVersion extends ReportSummary { markdown_text: string; current_warnings: string[] }

const strings = (value: Record<string, unknown>, keys: string[]) => keys.every(key => typeof value[key] === 'string')
const optional = (value: unknown) => value === null || typeof value === 'string'
function savedUrl(value: unknown): value is SavedUrl { return record(value) && strings(value, ['id', 'original_url', 'canonical_url', 'created_at']) && optional(value.note) && value.retrieved === false }
function evidencePassage(value: unknown): value is EvidencePassage { return record(value) && strings(value, ['id', 'display_id', 'source_id', 'source_status', 'source_origin', 'original_url', 'text', 'extraction_version']) && optional(value.source_title) && Number.isInteger(value.start_offset) && Number.isInteger(value.end_offset) }
function evidenceNote(value: unknown): value is EvidenceNote { return record(value) && strings(value, ['id', 'passage_id', 'display_id', 'source_id', 'target_key', 'target_label', 'stance', 'updated_at']) && typeof value.target_current === 'boolean' && optional(value.note) && Number.isInteger(value.revision_no) }
function citation(value: unknown): value is Citation { return record(value) && strings(value, ['id', 'passage_id', 'display_id', 'source_id', 'relation', 'passage_text']) && optional(value.quoted_text) && typeof value.reference_valid === 'boolean' && (value.quote_valid === null || typeof value.quote_valid === 'boolean') }
function claim(value: unknown): value is Claim { return record(value) && strings(value, ['id', 'claim_type', 'claim_text', 'evidence_state']) && Array.isArray(value.citations) && value.citations.every(citation) }
function answer(value: unknown): value is Answer { return record(value) && optional(value.id) && Number.isInteger(value.revision_no) && ANSWER_FIELDS.every(key => optional(value[key])) && Array.isArray(value.claims) && value.claims.every(claim) }
function reportSummary(value: unknown): value is ReportSummary { return record(value) && Number.isInteger(value.version_no) && strings(value, ['created_at', 'markdown_sha256', 'mode']) && record(value.validation_summary) }
function reportVersion(value: unknown): value is ReportVersion { return reportSummary(value) && typeof (value as unknown as ReportVersion).markdown_text === 'string' && Array.isArray((value as unknown as ReportVersion).current_warnings) }
const base = (id: string) => `/api/investigations/${encodeURIComponent(id)}`

export async function listSavedUrls(id: string) { return checked(await request(`${base(id)}/saved-urls`), arrayOf(savedUrl)) }
export async function saveUrl(id: string, key: string, url: string, note: string | null) { return checked(await request(`${base(id)}/saved-urls`, 'POST', { id: key, url, note }), savedUrl) }
export async function listEvidencePassages(id: string, offset = 0) { return checked(await request(`${base(id)}/passages?offset=${offset}`), arrayOf(evidencePassage)) }
export async function listNotes(id: string) { return checked(await request(`${base(id)}/evidence-notes`), arrayOf(evidenceNote)) }
export async function saveNote(id: string, note: { id: string; passage_id: string; target_key: string; stance: Stance; note: string | null; expected_revision: number }) { return checked(await request(`${base(id)}/evidence-notes`, 'PUT', note), evidenceNote) }
export async function getAnswer(id: string) { return checked(await request(`${base(id)}/answer`), answer) }
export async function saveAnswer(id: string, fields: Record<AnswerField, string | null>, claims: ClaimDraft[], revision: number) { return checked(await request(`${base(id)}/answer`, 'PUT', { ...fields, claims, expected_revision: revision }), answer) }
export async function listReports(id: string) { return checked(await request(`${base(id)}/reports`), arrayOf(reportSummary)) }
export async function getReport(id: string, version: number) { return checked(await request(`${base(id)}/reports/${version}`), reportVersion) }
export async function createReport(id: string, revision: number) { return checked(await request(`${base(id)}/reports`, 'POST', { expected_revision: revision }), reportVersion) }
export const reportDownloadUrl = (id: string, version: number) => `${base(id)}/reports/${version}/download`

// M1: research pipeline, provider setup and investigation lifecycle.
export interface Progress { status: string; error_code: string | null; cancel_requested: boolean; mode: string; scope: string; budgets: Budgets | null; narrow_reason: string | null; queries: { query_text: string; status: string; searched_at: string | null; results_count: number | null }[]; stages: { stage_key: string; stage_revision: number; status: string; completed_at: string | null; error_code: string | null }[]; usage: { search_attempts: number; model_attempts: number; pages_retrieved: number; pages_attempted: number; estimated_tokens: number } }
export interface RunEvent { id: string; event_type: string; created_at: string }
export interface GeneratedCitation { passage_id: string; display_id: string; source_id: string; source_title: string | null; source_status?: string; original_url: string; fetched_at: string | null; quoted_text: string | null; start_offset: number; end_offset: number; passage_text: string; reference_valid: boolean; quote_valid: boolean | null; invalid_reason: string | null }
export interface GeneratedClaim { ordinal: number; claim_text: string; evidence_state: 'cited' | 'not_established'; explanation: string | null; citations: GeneratedCitation[] }
export interface GeneratedAnswer { run_id: string; provider_id: string; model_id: string; prompt_version: string; generated_at: string; mode: string; status: string; summary_text: string; limitations_text: string | null; needed_evidence_text: string | null; suppressed_citations: number; claims: GeneratedClaim[] }
export interface GeneratedReportSummary { version_no: number; run_id: string; created_at: string; markdown_sha256: string; mode: string; prompt_version: string; report_schema_version: string; validation_summary: Record<string, number> }
export interface GeneratedReport extends GeneratedReportSummary { markdown_text: string; current_warnings: string[] }
function progressShape(value: unknown): value is Progress { return record(value) && typeof value.status === 'string' && Array.isArray(value.stages) && record(value.usage) }
function generatedCitation(value: unknown): value is GeneratedCitation { return record(value) && strings(value, ['passage_id', 'display_id', 'original_url', 'passage_text']) && typeof value.reference_valid === 'boolean' }
function generatedClaim(value: unknown): value is GeneratedClaim { return record(value) && strings(value, ['claim_text', 'evidence_state']) && Array.isArray(value.citations) && value.citations.every(generatedCitation) }
function generatedAnswer(value: unknown): value is GeneratedAnswer { return record(value) && strings(value, ['provider_id', 'model_id', 'prompt_version', 'mode', 'summary_text']) && Array.isArray(value.claims) && value.claims.every(generatedClaim) }
function generatedSummary(value: unknown): value is GeneratedReportSummary { return record(value) && Number.isInteger(value.version_no) && strings(value, ['created_at', 'markdown_sha256']) && record(value.validation_summary) }
function generatedReport(value: unknown): value is GeneratedReport { return generatedSummary(value) && typeof (value as unknown as GeneratedReport).markdown_text === 'string' && Array.isArray((value as unknown as GeneratedReport).current_warnings) }
export async function generatePlan(id: string, key: string, revision: number, replace: boolean) { await request(`${base(id)}/plan/generate`, 'POST', { id: key, expected_revision: revision, replace }) }
export async function startResearch(id: string, key: string, revision: number, budgets: Budgets) { await request(`${base(id)}/research`, 'POST', { id: key, expected_revision: revision, budgets }) }
export async function getProgress(run: string, investigation: string) { return checked(await request(`/api/runs/${encodeURIComponent(run)}/progress?${owned(investigation)}`), progressShape) }
export async function getGeneratedAnswer(id: string) {
  const value = await request(`${base(id)}/generated-answer`)
  if (!record(value) || !(value.answer === null || generatedAnswer(value.answer))) throw new ApiError(502)
  return value.answer as GeneratedAnswer | null
}
export async function listGeneratedReports(id: string) { return checked(await request(`${base(id)}/generated-reports`), arrayOf(generatedSummary)) }
export async function getGeneratedReport(id: string, version: number) { return checked(await request(`${base(id)}/generated-reports/${version}`), generatedReport) }
function runEvent(value: unknown): value is RunEvent { return record(value) && strings(value, ['id', 'event_type', 'created_at']) }
export async function getRunEvents(run: string, investigation: string) { return checked(await request(`${base(investigation)}/events?run_id=${encodeURIComponent(run)}`), arrayOf(runEvent)) }
export interface Storage { bytes: number; warning_bytes: number; over_warning: boolean }
export async function getStorage(id: string): Promise<Storage> {
  const value = await request(`${base(id)}/storage`)
  if (!record(value) || typeof value.bytes !== 'number' || typeof value.warning_bytes !== 'number' || typeof value.over_warning !== 'boolean') throw new ApiError(502)
  return value as unknown as Storage
}
export const generatedDownloadUrl = (id: string, version: number) => `${base(id)}/generated-reports/${version}/download`
export async function setSensitive(id: string, value: boolean) { await request(`${base(id)}/sensitive`, 'POST', { value }) }
export async function setArchived(id: string, value: boolean) { await request(`${base(id)}/archive`, 'POST', { value }) }
export async function deleteInvestigation(id: string, title: string) { await request(base(id), 'DELETE', { confirm_title: title }) }
const provider = (id: string) => `/api/providers/${encodeURIComponent(id)}`
export async function saveCredential(id: string, value: string) { await request(`${provider(id)}/credential`, 'PUT', { value }) }
export async function removeCredential(id: string) { await request(`${provider(id)}/credential`, 'DELETE', {}) }
export async function grantConsent(id: string, version: string) { await request(`${provider(id)}/consent`, 'POST', { disclosure_version: version, free_tier_confirmed: true }) }
export async function revokeConsent(id: string) { await request(`${provider(id)}/consent`, 'DELETE', {}) }
export async function getMode(signal?: AbortSignal): Promise<string | null> {
  const response = await fetch('/api/capabilities', { signal, credentials: 'omit', cache: 'no-store' })
  if (!response.ok) return null
  const data: unknown = await response.json()
  return record(data) && typeof data.mode === 'string' ? data.mode : null
}
