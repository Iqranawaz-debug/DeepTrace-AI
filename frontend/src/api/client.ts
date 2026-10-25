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
export interface Investigation { id: string; title: string; question: string; description: string | null; status: 'draft'; created_at: string; updated_at: string }
export interface PlanItem { id: string; sub_question: string; search_query: string | null }
export interface Plan { id: string | null; revision_no: number; items: PlanItem[] }
export interface InvestigationList { items: Investigation[]; total: number }
export type Fields = Pick<Investigation, 'title' | 'question' | 'description'>

export class ApiError extends Error {
  status: number
  constructor(status: number) {
    super(status === 409 ? 'Newer changes exist. Your edits are still here. Copy them before loading the latest saved version.' : status === 403 ? 'Local session expired or request denied. Your edits are still here. Retry to renew the session.' : status === 422 ? 'Check required fields and input limits. Your edits are still here.' : 'The local request failed. Your edits are still here. Check the backend and retry.')
    this.status = status
  }
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
    if (!response.ok) throw new ApiError(response.status)
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
