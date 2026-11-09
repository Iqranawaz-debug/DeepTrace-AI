import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import { Pencil, Play, SlidersHorizontal, Square } from 'lucide-react'
import { getInvestigation, getPlan, startResearch, type Budgets, type Investigation, type Plan } from '../../api/client'
import { InvestigationForm } from '../investigations/InvestigationForm'
import { ResearchTracker } from '../research/ResearchTracker'
import { EvidenceInspector } from './EvidenceInspector'
import { ACTIVE, BUDGET_LABELS, FAILURES, STATUS_TEXT, useResearch, useWorkspace, WorkspaceProvider, type Research } from './workspace'

const TABS = [['', 'Plan'], ['findings', 'Findings'], ['sources', 'Sources'], ['evidence', 'Evidence'], ['report', 'Report']] as const

export function InvestigationLayout() {
  const { id = '' } = useParams()
  const [data, setData] = useState<{ investigation: Investigation; plan: Plan }>()
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [planView, setPlanView] = useState(0)
  const openerRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    let active = true
    Promise.all([getInvestigation(id), getPlan(id)]).then(([investigation, plan]) => { if (active) setData({ investigation, plan }) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, attempt])
  const reloadInvestigation = useCallback(() => {
    void getInvestigation(id).then(investigation => setData(current => current && { ...current, investigation })).catch(() => {})
  }, [id])
  const research = useResearch(id, data?.investigation, reloadInvestigation)
  if (error) return <><h1 tabIndex={-1}>Investigation unavailable</h1><div role="alert" className="error-state">Could not open this investigation. It may be unavailable.<button className="button secondary" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Retry investigation</button></div></>
  if (!data) return <div className="ws-loading" aria-busy="true"><h1 tabIndex={-1} className="sr-only">Investigation</h1><p role="status">Loading investigation…</p><span className="skeleton-line" /><span className="skeleton-line short" /><span className="skeleton-block" /></div>
  const workspace = {
    id, investigation: data.investigation, plan: data.plan, planView, research, openerRef,
    setInvestigation: (investigation: Investigation) => setData(current => current && { ...current, investigation }),
    reloadInvestigation,
    reloadPlan: (remount = false) => {
      void Promise.all([getInvestigation(id), getPlan(id)]).then(([investigation, plan]) => {
        setData({ investigation, plan }); if (remount) setPlanView(view => view + 1)
      }).catch(() => { /* The saved plan remains confirmed. */ })
    },
  }
  return <WorkspaceProvider value={workspace}>
    <div className="ws">
      <WorkspaceHeader />
      <div className="ws-grid">
        <Outline />
        <div className="ws-center">
          <Notices research={research} />
          <nav className="ws-tabs" aria-label="Investigation sections">{TABS.map(([path, label]) =>
            <NavLink key={label} to={`/investigations/${encodeURIComponent(id)}${path ? `/${path}` : ''}`} end>{label}{label === 'Findings' && research.answer ? <span className="tab-count">{research.answer.claims.length}</span> : null}</NavLink>)}</nav>
          <div className="ws-panel"><Outlet /></div>
        </div>
        <EvidenceInspector />
      </div>
    </div>
  </WorkspaceProvider>
}

function WorkspaceHeader() {
  const { id, investigation, plan, research, setInvestigation } = useWorkspace()
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const { busy, blocked, activeRun, budgets, latest, progress } = research
  const canStart = !busy && !blocked && !activeRun && plan.items.length > 0 && !!budgets
  const hint = activeRun ? '' : blocked ? '' : plan.items.length ? 'Runs your saved plan. Unsaved edits are not included.' : 'Add at least one plan step first.'
  return <header className="ws-header">
    <div className="ws-title">
      <p className="eyebrow"><Link to="/investigations">Investigations</Link> <span aria-hidden="true">/</span> <span className="chip">{investigation.lifecycle ?? 'Draft'}</span>{investigation.sensitive && <span className="chip chip-warning">Sensitive</span>}{investigation.archived_at && <span className="chip">Archived</span>}</p>
      <h1 tabIndex={-1}>{investigation.title}</h1>
    </div>
    <div className="ws-actions">
      <Dialog.Root open={editing} onOpenChange={setEditing}><Dialog.Trigger asChild><button className="button secondary"><Pencil size={16} aria-hidden="true" />Edit</button></Dialog.Trigger>
        <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog wide-dialog"><Dialog.Title>Edit investigation</Dialog.Title><Dialog.Description>Title, question and description are saved on this computer.</Dialog.Description>
          <InvestigationForm initial={investigation} onSaved={saved => { setInvestigation(saved); setEditing(false) }} />
          <Dialog.Close className="button secondary">Close</Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root>
      <RunSettings research={research} />
      {activeRun && latest && ACTIVE.includes(latest.status) && <Dialog.Root open={confirming} onOpenChange={setConfirming}><Dialog.Trigger asChild><button className="button secondary" disabled={busy || progress?.cancel_requested}><Square size={14} aria-hidden="true" />{progress?.cancel_requested ? 'Cancelling…' : 'Cancel'}</button></Dialog.Trigger>
        <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog"><Dialog.Title>Cancel this run?</Dialog.Title><Dialog.Description>Evidence collected so far is kept.</Dialog.Description>
          <div className="actions"><Dialog.Close className="button secondary">Keep running</Dialog.Close><button className="button primary" onClick={() => { setConfirming(false); research.cancel(latest.id) }}>Cancel run</button></div></Dialog.Content></Dialog.Portal></Dialog.Root>}
      <button className="button primary" disabled={!canStart} aria-describedby={hint ? 'start-hint' : undefined} onClick={() => budgets && void research.begin('research', (key, revision) => startResearch(id, key, revision, budgets))}><Play size={16} aria-hidden="true" />Start research</button>
      {hint && <span id="start-hint" className="ws-hint">{hint}</span>}
    </div>
  </header>
}

function RunSettings({ research }: { research: Research }) {
  const { providers, budgets, setBudgets } = research
  const ceilings = providers?.budget_ceilings
  return <Dialog.Root><Dialog.Trigger asChild><button className="button secondary" disabled={!budgets || !ceilings}><SlidersHorizontal size={16} aria-hidden="true" />Run settings</button></Dialog.Trigger>
    <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog wide-dialog"><Dialog.Title>Run settings</Dialog.Title>
      <Dialog.Description>Limits are ceilings, not targets. A run stops with “Budget reached” and keeps what it found. Source types: web pages (HTML and plain text); JavaScript is not run.</Dialog.Description>
      {budgets && ceilings && <div className="budget-grid">{(Object.keys(BUDGET_LABELS) as (keyof Budgets)[]).map(name => <label key={name} className="field">{BUDGET_LABELS[name]}<input type="number" min={name === 'max_tokens' ? 1000 : 1} max={ceilings[name]} value={budgets[name]} onChange={event => setBudgets({ ...budgets, [name]: Number(event.target.value) })} /><span>Up to {ceilings[name].toLocaleString()}</span></label>)}</div>}
      <p className="record-dates">These limits apply to the next run you start from this page.</p>
      <div className="actions"><Dialog.Close className="button primary">Done</Dialog.Close></div></Dialog.Content></Dialog.Portal></Dialog.Root>
}

function Notices({ research }: { research: Research }) {
  const { waiting, blocked, modelBlocked, error, notice, providers } = research
  if (!waiting && !blocked && !modelBlocked && !error && !notice) return null
  return <div className="ws-notices">
    {waiting && <p role="status" className="mode-note">{waiting}</p>}
    {blocked && <p className="mode-note">{blocked}{providers?.mode === 'live_free' && (providers.blockers ?? []).length > 0 && <> <Link to="/setup">Open setup</Link></>}</p>}
    {modelBlocked && <p className="mode-note">Marked sensitive: a hosted model cannot be used, so plans and answers cannot be generated. Search and page retrieval still run.</p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className="error-state">{error}</p>}
  </div>
}

function Outline() {
  const { id, investigation, plan, research } = useWorkspace()
  const { latest, progress } = research
  return <aside className="ws-outline" aria-label="Investigation outline">
    <section><h2 className="outline-label">Question</h2><p className="outline-question">{investigation.question}</p>
      {investigation.description && <p className="outline-muted">{investigation.description}</p>}</section>
    <section><h2 className="outline-label">Plan · {plan.items.length} {plan.items.length === 1 ? 'step' : 'steps'}</h2>
      {plan.items.length ? <ol className="outline-steps">{plan.items.map(item => <li key={item.id}>{item.sub_question}</li>)}</ol>
        : <p className="outline-muted">No plan yet. <Link to={`/investigations/${encodeURIComponent(id)}`}>Write or generate one</Link>.</p>}</section>
    <section><h2 className="outline-label">Research run</h2>
      {!latest ? <p className="outline-muted">No research run yet.</p> : <>
        <p className="outline-status"><strong>{latest.mode === 'mock' ? 'SIMULATED · ' : ''}{progress?.cancel_requested && ACTIVE.includes(latest.status) ? 'Cancelling' : STATUS_TEXT[latest.status] ?? latest.status}</strong> · {latest.scope === 'plan_generation' ? 'Plan generation' : 'Research'}</p>
        {latest.error_code && !ACTIVE.includes(latest.status) && <p className="outline-reason">{FAILURES[latest.error_code] ?? 'This run stopped early.'} Saved sources are kept.</p>}
        {progress && latest.scope === 'research_pipeline' && progress.scope === 'research_pipeline' && <ResearchTracker progress={progress} vertical />}
        {progress && <p className="outline-muted">{progress.usage.search_attempts} searches · {progress.usage.pages_retrieved} pages · {progress.usage.model_attempts} model calls · ~{progress.usage.estimated_tokens.toLocaleString()} tokens</p>}
      </>}</section>
  </aside>
}
