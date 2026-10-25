import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getInvestigation, getPlan, type Investigation, type Plan } from '../../api/client'
import { InvestigationForm } from './InvestigationForm'
import { PlanEditor } from '../plans/PlanEditor'

export function InvestigationPage() {
  const { id = '' } = useParams()
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<{ investigation: Investigation; plan: Plan }>()
  const [error, setError] = useState(false)
  useEffect(() => {
    let active = true
    Promise.all([getInvestigation(id), getPlan(id)]).then(([investigation, plan]) => { if (active) setData({ investigation, plan }) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, attempt])
  return <><div className="page-intro"><p className="eyebrow">Draft · Stored on this computer</p><h1 tabIndex={-1}>Investigation workspace</h1><p>Manual planning only. No searches, AI generation or research execution.</p></div>
    {error ? <div role="alert" className="error-state">Could not open this investigation. It may be unavailable.<button className="button secondary" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Retry investigation</button></div> : !data ? <p role="status">Loading investigation…</p> : <>
      <p className="record-dates">Created {new Date(data.investigation.created_at).toLocaleString()} · Updated {new Date(data.investigation.updated_at).toLocaleString()}</p>
      <InvestigationForm initial={data.investigation} onSaved={investigation => setData({ ...data, investigation })} />
      <PlanEditor investigationId={id} initial={data.plan} onSaved={async () => {
        // Refresh activity display only; never replace unsaved form fields.
        try { const investigation = await getInvestigation(id); setData(current => current ? { ...current, investigation } : current) } catch { /* Saved plan remains confirmed. */ }
      }} />
      <p>To resolve a conflict, copy your unsaved edits, then refresh and confirm discarding them to load the latest saved version.</p>
    </>}
  </>
}
