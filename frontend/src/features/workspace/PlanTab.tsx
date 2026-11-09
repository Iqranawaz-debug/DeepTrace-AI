import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { generatePlan } from '../../api/client'
import { ManageInvestigation } from '../investigations/ManageInvestigation'
import { PlanEditor } from '../plans/PlanEditor'
import { ActivityLog } from '../research/ResearchTracker'
import { ACTIVE, banner, FAILURES, STATUS_TEXT, useWorkspace } from './workspace'

export function PlanTab() {
  const { id, plan, planView, research, investigation, reloadPlan, reloadInvestigation } = useWorkspace()
  const [replace, setReplace] = useState(false)
  const { busy, blocked, activeRun, modelBlocked, planReady, progress, latest, providers, mock } = research
  return <>
    <section className="card" aria-labelledby="generate-title">
      <div className="card-head"><h2 id="generate-title"><Sparkles size={16} aria-hidden="true" /> Starting point</h2></div>
      <p className="card-text">{mock ? 'Mock mode: a simulated model drafts plans from synthetic fixtures. Nothing leaves this computer and nothing here is real research.' : providers?.mode === 'live_free' ? <>Live mode: your question goes to Gemini to draft a plan. Starting research sends queries to Tavily and requests pages from public websites. Review this in <Link to="/settings">Settings</Link>.</> : 'Saved research can be read here.'}</p>
      <p className="card-text">{plan.items.length ? `Your saved plan has ${plan.items.length} step(s).` : 'No plan yet. Write one below, or generate a starting point.'} Generated plans can be edited before you start.</p>
      {plan.items.length > 0 && <label className="check-row"><input type="checkbox" checked={replace} onChange={event => setReplace(event.target.checked)} /> Replace my saved plan with a generated one</label>}
      <div className="actions"><button className="button secondary" disabled={busy || !!blocked || !!activeRun || modelBlocked || (plan.items.length > 0 && !replace)} onClick={() => void research.begin('plan', (key, revision) => generatePlan(id, key, revision, replace))}>Generate plan</button></div>
      {planReady && <p role="status" className="mode-note">The generated plan is saved{progress?.narrow_reason ? ` (${progress.narrow_reason})` : ''}. <button className="button secondary small" onClick={() => { research.dismissPlanReady(); setReplace(false); reloadPlan(true) }}>Show generated plan</button></p>}
    </section>
    <PlanEditor key={planView} investigationId={id} initial={plan} onSaved={() => reloadPlan(false)} />
    {latest && <section className="card" aria-labelledby="run-title"><div className="card-head"><h2 id="run-title">Latest run</h2><span className="chip">{latest.mode === 'mock' ? 'SIMULATED · ' : ''}{progress?.cancel_requested && ACTIVE.includes(latest.status) ? 'Cancelling' : STATUS_TEXT[latest.status] ?? latest.status}</span></div>
      <p className="card-text">{latest.scope === 'plan_generation' ? 'Plan generation' : 'Research'} · started {new Date(latest.created_at).toLocaleString()}</p>
      {latest.scope === 'research_pipeline' && banner(latest.status, latest.error_code) && <p role="status" className="mode-note">{banner(latest.status, latest.error_code)}</p>}
      {latest.scope !== 'research_pipeline' && latest.error_code && <p className="mode-note">{FAILURES[latest.error_code] ?? 'This run stopped early.'} Everything saved so far is kept.</p>}
      {progress && <ActivityLog runId={latest.id} investigationId={id} progress={progress} />}
    </section>}
    <ManageInvestigation investigation={investigation} onChanged={reloadInvestigation} />
    <p className="outline-muted">To resolve a conflict, copy your unsaved edits, then refresh and confirm discarding them to load the latest saved version.</p>
  </>
}
