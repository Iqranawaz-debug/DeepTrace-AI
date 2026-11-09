import { createContext, useCallback, useContext, useEffect, useRef, useState, type RefObject } from 'react'
import {
  ApiError, cancelCollection, getGeneratedAnswer, getPlan, getProgress, getProviders, listRuns,
  type Budgets, type CollectionRun, type GeneratedAnswer, type Investigation, type Plan, type Progress, type Providers,
} from '../../api/client'

export const ACTIVE = ['queued', 'running']
export const BUDGET_LABELS: Record<keyof Budgets, string> = { max_searches: 'Search calls', max_pages: 'Pages fetched', max_steps: 'Workflow steps', max_tokens: 'Estimated tokens', max_minutes: 'Minutes' }
export const FAILURES: Record<string, string> = {
  auth_rejected: 'The provider rejected the API key. Check it in Settings.',
  consent_required: 'A provider disclosure is no longer accepted. Review it in Settings.',
  not_configured: 'A provider is not configured. Finish setup in Settings.',
  rate_limited: 'The provider is rate limiting requests. Wait a few minutes, then start research again.',
  unavailable: "A provider didn't respond, even after retries (Gemini's free tier is often busy). Wait a few minutes, then start research again.",
  timeout: 'A provider did not answer in time (the language model can be slow). Try again.',
  dns_failed: 'A website address could not be found.',
  robots_unavailable: "A website's robots.txt could not be read, so its page was skipped.",
  malformed_response: 'The model returned an invalid response, even after a retry.',
  sensitive_blocked: 'This investigation is marked sensitive, so nothing was sent to the hosted model.',
  quota_exhausted: 'The provider quota is exhausted. Nothing further was requested and no paid fallback exists.',
  search_budget: 'The search limit was reached.',
  page_budget: 'The page limit was reached.',
  token_budget: 'The token limit was reached before the model call.',
  step_budget: 'The step limit was reached.',
  process_interrupted: 'The application stopped during this run.',
  worker_failure: 'An unexpected local error stopped this run.',
}
export const STATUS_TEXT: Record<string, string> = { completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled', budget_reached: 'Budget reached', interrupted: 'Interrupted', queued: 'Queued', running: 'Running' }

/** DESIGN §9.6 status messages: what happened and what was kept. */
export function banner(status: string, code: string | null): string {
  const reason = code ? FAILURES[code] ?? 'This run stopped early.' : ''
  if (status === 'completed') return 'Research completed. Review the findings, the report and the limitations.'
  if (status === 'cancelled') return 'You cancelled this run. Saved evidence is kept.'
  if (status === 'interrupted') return "This run stopped when the app closed. Completed steps and sources are saved. Resume isn't available in this version."
  if (status === 'budget_reached') return `${reason} Partial results are shown and may be incomplete.`
  if (status === 'failed') return `${reason || 'This run failed.'} Everything saved so far is kept. You can start a new run after fixing this.`
  return ''
}

export interface Workspace {
  id: string
  investigation: Investigation
  plan: Plan
  /** Bumped only by an explicit user choice, so polling never discards unsaved plan edits. */
  planView: number
  setInvestigation: (investigation: Investigation) => void
  reloadInvestigation: () => void
  reloadPlan: (remount?: boolean) => void
  research: Research
  /** The control that opened the evidence inspector, so focus can return to it. */
  openerRef: RefObject<HTMLElement | null>
}

export interface Research {
  providers?: Providers
  runs: CollectionRun[]
  latest?: CollectionRun
  activeRun?: CollectionRun
  progress?: Progress
  budgets?: Budgets
  setBudgets: (budgets: Budgets) => void
  busy: boolean
  error: string
  notice: string
  planReady: boolean
  dismissPlanReady: () => void
  resultKey: number
  answer: GeneratedAnswer | null
  answerLoaded: boolean
  mock: boolean
  /** Why new research cannot start right now, or ''. */
  blocked: string
  modelBlocked: boolean
  /** One explanation while something runs, instead of several disabled controls saying different things. */
  waiting: string
  begin: (action: string, run: (key: string, revision: number) => Promise<unknown>) => Promise<void>
  cancel: (runId: string) => void
}

const Context = createContext<Workspace | null>(null)
export const WorkspaceProvider = Context.Provider
export function useWorkspace(): Workspace {
  const value = useContext(Context)
  if (!value) throw new Error('useWorkspace must be used inside an investigation')
  return value
}

/** Polls providers, runs and the newest pipeline run around 1 Hz while the page is visible (ARCHITECTURE §11). */
export function useResearch(investigationId: string, investigation: Investigation | undefined, onFinished: () => void): Research {
  const [providers, setProviders] = useState<Providers>()
  const [runs, setRuns] = useState<CollectionRun[]>([])
  const [progress, setProgress] = useState<Progress>()
  const [budgets, setBudgets] = useState<Budgets>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [planReady, setPlanReady] = useState(false)
  const [resultKey, setResultKey] = useState(0)
  const [answer, setAnswer] = useState<GeneratedAnswer | null>(null)
  const [answerLoaded, setAnswerLoaded] = useState(false)
  const key = useRef<{ action: string; id: string } | null>(null)
  const lastActive = useRef<string | null>(null)
  const finished = useRef(onFinished)
  useEffect(() => { finished.current = onFinished }, [onFinished])
  const refresh = useCallback(async () => {
    const [p, r] = await Promise.all([getProviders(), listRuns(investigationId)])
    const newest = r.find(run => run.scope && run.scope !== 'evidence_collection')
    // Fetch before publishing so the status line and its stages always describe the same run.
    const detail = newest ? await getProgress(newest.id, investigationId) : undefined
    setProviders(p); setRuns(r); setProgress(detail); setError(current => current.startsWith('Could not read research status') ? '' : current)
    setBudgets(current => current ?? p.budgets)
    if (newest) {
      if (ACTIVE.includes(newest.status)) lastActive.current = newest.id
      else if (lastActive.current === newest.id) {
        lastActive.current = null
        setResultKey(value => value + 1)
        finished.current()  // The header and Manage status read the new lifecycle.
        if (newest.scope === 'plan_generation' && newest.status === 'completed') setPlanReady(true)
      }
    }
  }, [investigationId])
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try { if (!stopped && document.visibilityState !== 'hidden') await refresh() } catch { if (!stopped) setError('Could not read research status. Saved work is unaffected. Retrying…') }
      if (!stopped) timer = setTimeout(poll, 1200)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [refresh])
  useEffect(() => {
    let active = true
    getGeneratedAnswer(investigationId).then(value => { if (active) { setAnswer(value); setAnswerLoaded(true) } }).catch(() => { if (active) setAnswerLoaded(true) })
    return () => { active = false }
  }, [investigationId, resultKey])
  async function begin(action: string, run: (id: string, revision: number) => Promise<unknown>) {
    setBusy(true); setError(''); setNotice(''); setPlanReady(false)
    try {
      // The saved plan revision is what runs; unsaved edits on screen are not included.
      const saved = await getPlan(investigationId)
      const signature = `${action}:${saved.revision_no}`
      if (key.current?.action !== signature) key.current = { action: signature, id: crypto.randomUUID() }
      await run(key.current.id, saved.revision_no)
      // A fast run can finish between polls; remember it so its completion is never missed.
      lastActive.current = key.current.id
      key.current = null
      await refresh()
    } catch (failure) {
      setError(failure instanceof ApiError ? [failure.message, failure.detail].filter(Boolean).join(' ') : 'The request could not be confirmed. Retry when the backend is available.')
    } finally { setBusy(false) }
  }
  function cancel(runId: string) {
    void cancelCollection(runId, investigationId).then(refresh).catch(() => setError('Cancellation could not be confirmed. Retry.'))
  }
  const pipelineRuns = runs.filter(run => run.scope && run.scope !== 'evidence_collection')
  const activeRun = runs.find(run => ACTIVE.includes(run.status))
  const mock = providers?.mode === 'mock'
  const blockers = providers?.blockers ?? []
  const blocked = !providers || !investigation ? '' : investigation.archived_at ? 'This investigation is archived.' : providers.mode === 'offline' ? 'Offline mode: new research is disabled.' : blockers.length ? blockers.join(' ') : mock && !providers.consent ? 'Enable synthetic collection in the Evidence tab first.' : ''
  const waiting = !activeRun ? '' : activeRun.scope === 'plan_generation'
    ? `${mock ? 'The simulated model' : 'Gemini'} is drafting your plan. ${mock ? '' : 'This can take up to 2½ minutes. '}Plan editing and research are paused until it finishes.`
    : activeRun.scope === 'research_pipeline' ? 'Research is running. Plan editing and new runs are paused until it finishes; you can cancel it from the header.'
    : 'A collection run is active. New runs wait until it finishes.'
  return {
    providers, runs, latest: pipelineRuns[0], activeRun, progress, budgets, setBudgets, busy, error, notice, planReady,
    dismissPlanReady: () => { setPlanReady(false); setNotice('') }, resultKey, answer, answerLoaded, mock, blocked,
    modelBlocked: !mock && !!investigation?.sensitive, waiting, begin, cancel,
  }
}
