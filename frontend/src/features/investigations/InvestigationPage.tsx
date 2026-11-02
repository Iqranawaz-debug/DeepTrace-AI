import { useEffect, useState } from 'react'
import { EvidenceWorkspace } from '../evidence/EvidenceWorkspace'
import { useParams } from 'react-router-dom'
import { getInvestigation, getPlan, type Investigation, type Plan } from '../../api/client'
import { InvestigationForm } from './InvestigationForm'
import { PlanEditor } from '../plans/PlanEditor'
import { ResearchPanel } from '../research/ResearchPanel'
import { InvestigationNav } from './InvestigationNav'
import { ManageInvestigation } from './ManageInvestigation'

export function InvestigationPage() {
  const { id = '' } = useParams()
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<{ investigation: Investigation; plan: Plan }>()
  const [error, setError] = useState(false)
  // Bumped only by an explicit user choice, so polling can never discard unsaved plan edits.
  const [planView, setPlanView] = useState(0)
  useEffect(() => {
    let active = true
    Promise.all([getInvestigation(id), getPlan(id)]).then(([investigation, plan]) => { if (active) setData({ investigation, plan }) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, attempt])
  return <><div className="page-intro"><p className="eyebrow">{data?.investigation.lifecycle ?? 'Draft'} · Stored on this computer</p><h1 tabIndex={-1}>Investigation workspace</h1><p>Plan your question, run bounded research, and inspect every source and citation.</p></div>
    <InvestigationNav id={id} current="workspace" />
    {error ? <div role="alert" className="error-state">Could not open this investigation. It may be unavailable.<button className="button secondary" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Retry investigation</button></div> : !data ? <p role="status">Loading investigation…</p> : <>
      <p className="record-dates">Created {new Date(data.investigation.created_at).toLocaleString()} · Updated {new Date(data.investigation.updated_at).toLocaleString()}</p>
      <InvestigationForm initial={data.investigation} onSaved={investigation => setData({ ...data, investigation })} />
      <PlanEditor key={planView} investigationId={id} initial={data.plan} onSaved={async () => {
        // Refresh activity display only; never replace unsaved form fields.
        try { const [investigation, plan] = await Promise.all([getInvestigation(id), getPlan(id)]); setData(current => current ? { ...current, investigation, plan } : current) } catch { /* Saved plan remains confirmed. */ }
      }} />
      <ResearchPanel key={`research-${id}`} investigationId={id} plan={data.plan} sensitive={!!data.investigation.sensitive} archived={!!data.investigation.archived_at} onPlanGenerated={() => { void getPlan(id).then(plan => { setData(current => current ? { ...current, plan } : current); setPlanView(view => view + 1) }) }} />
      <EvidenceWorkspace key={id} investigationId={id} />
      <ManageInvestigation investigation={data.investigation} onChanged={() => { void getInvestigation(id).then(investigation => setData(current => current ? { ...current, investigation } : current)) }} />
      <p>To resolve a conflict, copy your unsaved edits, then refresh and confirm discarding them to load the latest saved version.</p>
    </>}
  </>
}
