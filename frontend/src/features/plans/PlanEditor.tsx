import { useState } from 'react'
import { savePlan, type Plan, type PlanItem } from '../../api/client'
import { useUnsaved } from '../investigations/InvestigationForm'

export function PlanEditor({ investigationId, initial, onSaved }: { investigationId: string; initial: Plan; onSaved: () => void }) {
  const [items, setItems] = useState(initial.items)
  const [baseline, setBaseline] = useState(initial.items)
  const [revision, setRevision] = useState(initial.revision_no)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [announcement, setAnnouncement] = useState('')
  const dirty = JSON.stringify(items) !== JSON.stringify(baseline)
  const clearDirty = useUnsaved(dirty, busy)
  function change(id: string, values: Partial<PlanItem>) { setItems(items.map(item => item.id === id ? { ...item, ...values } : item)) }
  function move(index: number, direction: number) {
    const next = [...items]; const target = index + direction
    ;[next[index], next[target]] = [next[target], next[index]]
    setItems(next); setAnnouncement(`Moved to position ${target + 1} of ${items.length}`)
  }
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError('')
    try {
      const saved = await savePlan(investigationId, items, revision)
      setItems(saved.items); setBaseline(saved.items); setRevision(saved.revision_no); clearDirty(); onSaved()
    } catch (error) { setError(error instanceof Error ? error.message : 'Save failed. Your edits are still here.') }
    finally { setBusy(false) }
  }
  return <form className="settings-card workspace-form" onSubmit={submit}>
    <h2>Manual research plan</h2><p>Up to eight steps. These are your planning notes, not AI output or research findings. Search-query notes are never executed.</p>
    <fieldset disabled={busy}><legend className="sr-only">Research steps</legend>
      {items.length === 0 && <p>No steps yet. You can save an empty draft plan.</p>}
      <ol className="plan-list">{items.map((item, index) => <li key={item.id} className="plan-step"><h3>Step {index + 1}</h3>
        <label className="field">Sub-question {index + 1}<textarea required maxLength={1000} rows={3} value={item.sub_question} onChange={e => change(item.id, { sub_question: e.target.value })} /><span>1–1,000 characters</span></label>
        <label className="field">Search-query note {index + 1} (optional)<input maxLength={500} value={item.search_query ?? ''} onChange={e => change(item.id, { search_query: e.target.value || null })} /><span>Up to 500 characters</span></label>
        <div className="actions"><button type="button" className="button secondary" disabled={index === 0} aria-label={`Move up step ${index + 1}`} onClick={() => move(index, -1)}>Move up</button><button type="button" className="button secondary" disabled={index === items.length - 1} aria-label={`Move down step ${index + 1}`} onClick={() => move(index, 1)}>Move down</button><button type="button" className="button secondary" aria-label={`Remove step ${index + 1}`} onClick={() => { setItems(items.filter(step => step.id !== item.id)); setAnnouncement(`Removed step ${index + 1}. Save the plan to apply removal.`) }}>Remove</button></div>
      </li>)}</ol>
      <button type="button" className="button secondary" disabled={items.length >= 8} onClick={() => setItems([...items, { id: crypto.randomUUID(), sub_question: '', search_query: null }])}>Add step</button>
    </fieldset>
    <p role="status">{announcement}</p>{error && <p role="alert" className="error-state">{error}</p>}
    <div className="actions"><button className="button primary" disabled={busy || (!dirty && revision > 0)}>{busy ? 'Saving plan…' : 'Save plan'}</button><span role="status">{busy ? 'Saving locally…' : dirty ? 'Unsaved plan' : revision ? `Plan saved locally · revision ${revision}` : 'Plan not saved yet'}</span></div>
  </form>
}
