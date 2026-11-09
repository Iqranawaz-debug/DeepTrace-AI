import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import { ApiError, cancelCollection, generatePlan, getPlan, getProgress, getProviders, listRuns, startResearch, type Budgets, type CollectionRun, type Plan, type Progress, type Providers } from '../../api/client'
import { GeneratedResults } from './GeneratedResults'
import { ActivityLog, ResearchTracker } from './ResearchTracker'

const ACTIVE = ['queued', 'running']
const BUDGET_LABELS: Record<keyof Budgets, string> = { max_searches: 'Search calls', max_pages: 'Pages fetched', max_steps: 'Workflow steps', max_tokens: 'Estimated tokens', max_minutes: 'Minutes' }
const FAILURES: Record<string, string> = {
  auth_rejected: 'The provider rejected the API key. Check it in Settings.',
  consent_required: 'A provider disclosure is no longer accepted. Review it in Settings.',
  not_configured: 'A provider is not configured. Finish setup in Settings.',
  rate_limited: 'The provider is rate limiting requests. Retry later.',
  unavailable: 'The provider is unavailable. Retry later.',
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
/** DESIGN §9.6 status messages: what happened and what was kept. */
function banner(status: string, code: string | null): string {
  const reason = code ? FAILURES[code] ?? 'This run stopped early.' : ''
  if (status === 'completed') return 'Research completed. Review the report and the limitations.'
  if (status === 'cancelled') return 'You cancelled this run. Saved evidence is kept.'
  if (status === 'interrupted') return "This run stopped when the app closed. Completed steps and sources are saved. Resume isn't available in this version."
  if (status === 'budget_reached') return `${reason} Partial results are shown and may be incomplete.`
  if (status === 'failed') return `${reason || 'This run failed.'} Everything saved so far is kept. You can start a new run after fixing this.`
  return ''
}
const STATUS_TEXT: Record<string, string> = { completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled', budget_reached: 'Budget reached', interrupted: 'Interrupted', queued: 'Queued', running: 'Running' }

export function ResearchPanel({ investigationId, plan, sensitive, archived, onPlanGenerated, onRunFinished }: { investigationId: string; plan: Plan; sensitive: boolean; archived: boolean; onPlanGenerated: () => void; onRunFinished?: () => void }) {
  const [providers, setProviders] = useState<Providers>()
  const [runs, setRuns] = useState<CollectionRun[]>([])
  const [progress, setProgress] = useState<Progress>()
  const [budgets, setBudgets] = useState<Budgets>()
  const [replace, setReplace] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [planReady, setPlanReady] = useState(false)
  const [resultKey, setResultKey] = useState(0)
  const [confirming, setConfirming] = useState(false)
  const key = useRef<{ action: string; id: string } | null>(null)
  const lastActive = useRef<string | null>(null)
  const finished = useRef(onRunFinished)
  useEffect(() => { finished.current = onRunFinished }, [onRunFinished])
  const pipelineRuns = runs.filter(run => run.scope && run.scope !== 'evidence_collection')
  const latest = pipelineRuns[0]
  const refresh = useCallback(async () => {
    const [p, r] = await Promise.all([getProviders(), listRuns(investigationId)])
    const newest = r.find(run => run.scope && run.scope !== 'evidence_collection')
    // Fetch before publishing so the status line and its stages always describe the same run.
    const detail = newest ? await getProgress(newest.id, investigationId) : undefined
    setProviders(p); setRuns(r); setProgress(detail)
    setBudgets(current => current ?? p.budgets)
    if (newest) {
      const active = ACTIVE.includes(newest.status)
      if (active) lastActive.current = newest.id
      else if (lastActive.current === newest.id) {
        lastActive.current = null
        setResultKey(value => value + 1)
        finished.current?.()  // The page header and Manage status read the new lifecycle.
        if (newest.scope === 'plan_generation' && newest.status === 'completed') setPlanReady(true)
      }
    }
  }, [investigationId])
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      // Around 1 Hz, and only while visible (ARCHITECTURE §11).
      try { if (!stopped && document.visibilityState !== 'hidden') await refresh() } catch { if (!stopped) setError('Could not read research status. Saved work is unaffected. Retrying…') }
      if (!stopped) timer = setTimeout(poll, 1200)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [refresh])
  async function begin(action: string, run: (id: string, revision: number) => Promise<unknown>, message: string) {
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
      setNotice(message)
      await refresh()
    } catch (failure) {
      setError(failure instanceof ApiError ? [failure.message, failure.detail].filter(Boolean).join(' ') : 'The request could not be confirmed. Retry when the backend is available.')
    } finally { setBusy(false) }
  }
  const mock = providers?.mode === 'mock'
  const reason = !providers ? '' : archived ? 'This investigation is archived.' : providers.mode === 'offline' ? 'Offline mode: new research is disabled.' : (providers.blockers ?? []).length ? (providers.blockers ?? []).join(' ') : mock && !providers.consent ? 'Enable synthetic collection in the Evidence workspace below first.' : ''
  const modelBlocked = !mock && sensitive
  const activeRun = runs.find(run => ACTIVE.includes(run.status))
  // One explanation while something runs, instead of several disabled controls saying different things.
  const waiting = !activeRun ? '' : activeRun.scope === 'plan_generation'
    ? `${mock ? 'The simulated model' : 'Gemini'} is drafting your plan. ${mock ? '' : 'This can take up to 2½ minutes. '}Plan editing and research are paused until it finishes.`
    : activeRun.scope === 'research_pipeline' ? 'Research is running. Plan editing and new runs are paused until it finishes; you can cancel it below.'
    : 'A collection run is active. New runs wait until it finishes.'
  return <section className="settings-card research-panel" aria-labelledby="research-title">
    <h2 id="research-title">Research</h2>
    <p>{mock ? 'Mock mode: simulated search and a simulated model use synthetic fixtures. Nothing leaves this computer and nothing here is real research.' : providers?.mode === 'live_free' ? <>Live mode: your queries go to Tavily, your question and selected passages go to Gemini, and pages are requested from public websites. Review this in <Link to="/settings">Settings</Link>.</> : 'Saved research can be read here.'}</p>
    {waiting && <p role="status" className="mode-note">{waiting}</p>}
    {reason && <p className="mode-note">{reason}{providers && providers.mode === 'live_free' && (providers.blockers ?? []).length > 0 && <> <Link to="/setup">Open setup</Link></>}</p>}
    {modelBlocked && <p className="mode-note">Marked sensitive: a hosted model cannot be used, so plans and answers cannot be generated. Search and page retrieval still run.</p>}

    <h3>1. Plan</h3>
    <p>{plan.items.length ? `Your saved plan has ${plan.items.length} step(s).` : 'No plan yet. Write one above, or generate a starting point.'} Generated plans can be edited before you start.</p>
    {plan.items.length > 0 && <label className="check-row"><input type="checkbox" checked={replace} onChange={event => setReplace(event.target.checked)} /> Replace my saved plan with a generated one</label>}
    <div className="actions"><button className="button secondary" disabled={busy || !!reason || !!activeRun || modelBlocked || (plan.items.length > 0 && !replace)} onClick={() => void begin('plan', (id, revision) => generatePlan(investigationId, id, revision, replace), '')}>Generate plan</button></div>
    {planReady && <p role="status" className="mode-note">The generated plan is saved{progress?.narrow_reason ? ` (${progress.narrow_reason})` : ''}. <button className="button secondary" onClick={() => { setPlanReady(false); setReplace(false); onPlanGenerated() }}>Show generated plan</button></p>}

    <h3>2. Limits</h3>
    <p>Limits are ceilings, not targets. Source types: web pages (HTML and plain text). JavaScript is not run. A run stops with “Budget reached” and keeps what it found.</p>
    {budgets && providers?.budget_ceilings && <div className="budget-grid">{(Object.keys(BUDGET_LABELS) as (keyof Budgets)[]).map(name => <label key={name} className="field">{BUDGET_LABELS[name]}<input type="number" min={name === 'max_tokens' ? 1000 : 1} max={providers.budget_ceilings?.[name]} value={budgets[name]} onChange={event => setBudgets({ ...budgets, [name]: Number(event.target.value) })} /><span>Up to {providers.budget_ceilings?.[name].toLocaleString()}</span></label>)}</div>}

    <h3>3. Start</h3>
    <div className="actions"><button className="button primary" disabled={busy || !!reason || !!activeRun || !plan.items.length || !budgets} onClick={() => budgets && void begin('research', (id, revision) => startResearch(investigationId, id, revision, budgets), '')}>Start research</button><span>{activeRun ? '' : plan.items.length ? 'Runs your saved plan. Unsaved edits are not included.' : 'Add at least one plan step first.'}</span></div>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className="error-state">{error}</p>}

    {latest && <div className="run-status"><h3>Latest run</h3>
      <p><strong>{latest.mode === 'mock' ? 'SIMULATED · ' : ''}{progress?.cancel_requested && ACTIVE.includes(latest.status) ? 'Cancelling' : STATUS_TEXT[latest.status] ?? latest.status}</strong> · {latest.scope === 'plan_generation' ? 'Plan generation' : 'Research'}</p>
      {banner(latest.status, latest.error_code) && latest.scope === 'research_pipeline' && <p role="status" className="mode-note">{banner(latest.status, latest.error_code)}</p>}
      {latest.scope !== 'research_pipeline' && latest.error_code && <p>{FAILURES[latest.error_code] ?? 'This run stopped early.'} Everything saved so far is kept.</p>}
      {progress && <>{latest.scope === 'research_pipeline' && progress.scope === 'research_pipeline' && <ResearchTracker progress={progress} />}
        <p className="record-dates">Search attempts {progress.usage.search_attempts} · pages retrieved {progress.usage.pages_retrieved} · model attempts {progress.usage.model_attempts} · about {progress.usage.estimated_tokens.toLocaleString()} tokens (estimate)</p>
        <ActivityLog runId={latest.id} investigationId={investigationId} progress={progress} /></>}
      {ACTIVE.includes(latest.status) && <Dialog.Root open={confirming} onOpenChange={setConfirming}><Dialog.Trigger asChild><button className="button secondary" disabled={busy || progress?.cancel_requested}>{progress?.cancel_requested ? 'Cancelling…' : 'Cancel'}</button></Dialog.Trigger>
        <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog"><Dialog.Title>Cancel this run?</Dialog.Title><Dialog.Description>Evidence collected so far is kept.</Dialog.Description>
          <div className="actions"><Dialog.Close className="button secondary">Keep running</Dialog.Close><button className="button primary" onClick={() => { setConfirming(false); void cancelCollection(latest.id, investigationId).then(refresh).catch(() => setError('Cancellation could not be confirmed. Retry.')) }}>Cancel run</button></div></Dialog.Content></Dialog.Portal></Dialog.Root>}
    </div>}
    <GeneratedResults key={resultKey} investigationId={investigationId} />
  </section>
}
