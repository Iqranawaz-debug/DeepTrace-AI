import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, cancelCollection, generatePlan, getPlan, getProgress, getProviders, listRuns, startResearch, type Budgets, type CollectionRun, type Plan, type Progress, type Providers } from '../../api/client'
import { GeneratedResults } from './GeneratedResults'

const ACTIVE = ['queued', 'running']
const STAGES: Record<string, string> = { plan: 'Plan generated', discover: 'Searched', fetch: 'Pages fetched', rank: 'Passages ranked', synthesize: 'Answer drafted', validate: 'Citations checked', report: 'Report saved' }
const BUDGET_LABELS: Record<keyof Budgets, string> = { max_searches: 'Search calls', max_pages: 'Pages fetched', max_steps: 'Workflow steps', max_tokens: 'Estimated tokens', max_minutes: 'Minutes' }
const FAILURES: Record<string, string> = {
  auth_rejected: 'The provider rejected the API key. Check it in Settings.',
  consent_required: 'A provider disclosure is no longer accepted. Review it in Settings.',
  not_configured: 'A provider is not configured. Finish setup in Settings.',
  rate_limited: 'The provider is rate limiting requests. Retry later.',
  unavailable: 'The provider is unavailable. Retry later.',
  timeout: 'The provider did not respond in time. Retry later.',
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
const STATUS_TEXT: Record<string, string> = { completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled', budget_reached: 'Budget reached', interrupted: 'Interrupted', queued: 'Queued', running: 'Running' }

export function ResearchPanel({ investigationId, plan, sensitive, archived, onPlanGenerated }: { investigationId: string; plan: Plan; sensitive: boolean; archived: boolean; onPlanGenerated: () => void }) {
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
  const key = useRef<{ action: string; id: string } | null>(null)
  const lastActive = useRef<string | null>(null)
  const pipelineRuns = runs.filter(run => run.scope && run.scope !== 'evidence_collection')
  const latest = pipelineRuns[0]
  const anyActive = runs.some(run => ACTIVE.includes(run.status))
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
  const reason = !providers ? '' : archived ? 'This investigation is archived.' : providers.mode === 'offline' ? 'Offline mode: new research is disabled.' : (providers.blockers ?? []).length ? (providers.blockers ?? []).join(' ') : mock && !providers.consent ? 'Enable synthetic collection in the Evidence workspace below first.' : anyActive ? 'A run is already active.' : ''
  const modelBlocked = !mock && sensitive
  return <section className="settings-card research-panel" aria-labelledby="research-title">
    <h2 id="research-title">Research</h2>
    <p>{mock ? 'Mock mode: simulated search and a simulated model use synthetic fixtures. Nothing leaves this computer and nothing here is real research.' : providers?.mode === 'live_free' ? <>Live mode: your queries go to Tavily, your question and selected passages go to Gemini, and pages are requested from public websites. Review this in <Link to="/settings">Settings</Link>.</> : 'Saved research can be read here.'}</p>
    {reason && <p className="mode-note">{reason}{providers && providers.mode === 'live_free' && (providers.blockers ?? []).length > 0 && <> <Link to="/setup">Open setup</Link></>}</p>}
    {modelBlocked && <p className="mode-note">Marked sensitive: a hosted model cannot be used, so plans and answers cannot be generated. Search and page retrieval still run.</p>}

    <h3>1. Plan</h3>
    <p>{plan.items.length ? `Your saved plan has ${plan.items.length} step(s).` : 'No plan yet. Write one above, or generate a starting point.'} Generated plans can be edited before you start.</p>
    {plan.items.length > 0 && <label className="check-row"><input type="checkbox" checked={replace} onChange={event => setReplace(event.target.checked)} /> Replace my saved plan with a generated one</label>}
    <div className="actions"><button className="button secondary" disabled={busy || !!reason || modelBlocked || (plan.items.length > 0 && !replace)} onClick={() => void begin('plan', (id, revision) => generatePlan(investigationId, id, revision, replace), 'Generating a plan.')}>Generate plan</button></div>
    {planReady && <p role="status" className="mode-note">The generated plan is saved{progress?.narrow_reason ? ` (${progress.narrow_reason})` : ''}. <button className="button secondary" onClick={() => { setPlanReady(false); setReplace(false); onPlanGenerated() }}>Show generated plan</button></p>}

    <h3>2. Limits</h3>
    <p>Source types: web pages (HTML and plain text). JavaScript is not run. These are upper limits, not targets; a run stops with “Budget reached” and keeps what it found.</p>
    {budgets && providers?.budget_ceilings && <div className="budget-grid">{(Object.keys(BUDGET_LABELS) as (keyof Budgets)[]).map(name => <label key={name} className="field">{BUDGET_LABELS[name]}<input type="number" min={name === 'max_tokens' ? 1000 : 1} max={providers.budget_ceilings?.[name]} value={budgets[name]} onChange={event => setBudgets({ ...budgets, [name]: Number(event.target.value) })} /><span>Up to {providers.budget_ceilings?.[name].toLocaleString()}</span></label>)}</div>}

    <h3>3. Start</h3>
    <div className="actions"><button className="button primary" disabled={busy || !!reason || !plan.items.length || !budgets} onClick={() => budgets && void begin('research', (id, revision) => startResearch(investigationId, id, revision, budgets), 'Research started.')}>Start research</button><span>{plan.items.length ? 'Runs your saved plan. Unsaved edits are not included.' : 'Add at least one plan step first.'}</span></div>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className="error-state">{error}</p>}

    {latest && <div className="run-status" aria-live="polite"><h3>Latest run</h3>
      <p><strong>{latest.mode === 'mock' ? 'SIMULATED · ' : ''}{progress?.cancel_requested && ACTIVE.includes(latest.status) ? 'Cancelling' : STATUS_TEXT[latest.status] ?? latest.status}</strong> · {latest.scope === 'plan_generation' ? 'Plan generation' : 'Research'}</p>
      {latest.error_code && <p>{FAILURES[latest.error_code] ?? 'This run stopped early.'} Everything saved so far is kept.</p>}
      {progress && <><ul className="stage-list">{progress.stages.filter(stage => STAGES[stage.stage_key]).map(stage => <li key={`${stage.stage_key}-${stage.stage_revision}`}>{STAGES[stage.stage_key]}</li>)}</ul>
        <p className="record-dates">Search attempts {progress.usage.search_attempts} · pages retrieved {progress.usage.pages_retrieved} · model attempts {progress.usage.model_attempts} · about {progress.usage.estimated_tokens.toLocaleString()} tokens (estimate)</p></>}
      {ACTIVE.includes(latest.status) && <button className="button secondary" disabled={busy || progress?.cancel_requested} onClick={() => void cancelCollection(latest.id, investigationId).then(refresh).catch(() => setError('Cancellation could not be confirmed. Retry.'))}>{progress?.cancel_requested ? 'Cancelling…' : 'Cancel run'}</button>}
    </div>}
    <GeneratedResults key={resultKey} investigationId={investigationId} />
  </section>
}
