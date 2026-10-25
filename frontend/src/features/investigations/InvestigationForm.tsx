import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Link, useBlocker, useNavigate } from 'react-router-dom'
import { createInvestigation, editInvestigation, type Fields, type Investigation } from '../../api/client'

const DirtyContext = createContext<(id: string, dirty: boolean, busy: boolean) => void>(() => {})

export function UnsavedChanges({ children }: { children: ReactNode }) {
  const dirty = useRef(new Set<string>())
  const pending = useRef(new Set<string>())
  const [saving, setSaving] = useState(false)
  const update = useCallback((id: string, value: boolean, busy: boolean) => {
    if (value || busy) dirty.current.add(id); else dirty.current.delete(id)
    if (busy) pending.current.add(id); else pending.current.delete(id)
    setSaving(pending.current.size > 0)
  }, [])
  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirty.current.size > 0 && currentLocation.pathname !== nextLocation.pathname)
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => { if (dirty.current.size) { event.preventDefault(); event.returnValue = '' } }
    window.addEventListener('beforeunload', beforeUnload)
    return () => window.removeEventListener('beforeunload', beforeUnload)
  }, [])
  return <DirtyContext.Provider value={update}>{children}{blocker.state === 'blocked' && <Dialog.Root open onOpenChange={open => { if (!open) blocker.reset() }}><Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog"><Dialog.Title>Leave unsaved changes?</Dialog.Title><Dialog.Description>Your unsaved edits will be lost. Saved work stays on this computer. {saving && "A save is in progress; wait for it to finish before leaving."}</Dialog.Description><div className="actions"><button className="button primary" onClick={() => blocker.reset()}>Keep editing</button><button className="button secondary" disabled={saving} onClick={() => { dirty.current.clear(); blocker.proceed() }}>Discard and leave</button></div></Dialog.Content></Dialog.Portal></Dialog.Root>}</DirtyContext.Provider>
}

// Shared with the plan editor so there is one router blocker for the whole page.
// eslint-disable-next-line react-refresh/only-export-components
export function useUnsaved(dirty: boolean, busy = false) {
  const id = useId()
  const update = useContext(DirtyContext)
  useEffect(() => { update(id, dirty, busy); return () => update(id, false, false) }, [id, dirty, busy, update])
  return () => update(id, false, false)
}

export function InvestigationForm({ initial, onSaved }: { initial?: Investigation; onSaved?: (value: Investigation) => void }) {
  const [fields, setFields] = useState<Fields>({ title: initial?.title ?? '', question: initial?.question ?? '', description: initial?.description ?? '' })
  const [baseline, setBaseline] = useState(fields)
  const timestamp = useRef(initial?.updated_at ?? '')
  useEffect(() => {
    if (initial && initial.title === baseline.title && initial.question === baseline.question && (initial.description ?? '') === (baseline.description ?? '')) timestamp.current = initial.updated_at
  }, [initial, baseline])
  const [identifier] = useState(() => initial?.id ?? crypto.randomUUID())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const dirty = JSON.stringify(fields) !== JSON.stringify(baseline)
  const clearDirty = useUnsaved(dirty, busy)
  const navigate = useNavigate()
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (!fields.title.trim() || fields.question.trim().length < 10) { setError('Enter a title and a research question of at least 10 characters, excluding surrounding spaces.'); return }
    setBusy(true); setError('')
    try {
      const saved = initial ? await editInvestigation(identifier, fields, timestamp.current) : await createInvestigation(identifier, fields)
      const values = { title: saved.title, question: saved.question, description: saved.description ?? '' }
      setFields(values); setBaseline(values); timestamp.current = saved.updated_at; clearDirty(); onSaved?.(saved)
      if (!initial) await navigate(`/investigations/${saved.id}`)
    } catch (error) { setError(error instanceof Error ? error.message : 'Save failed. Your edits are still here.') }
    finally { setBusy(false) }
  }
  return <form className="workspace-form settings-card" onSubmit={submit}>
    <h2>{initial ? 'Investigation details' : 'Your research question'}</h2>
    <fieldset disabled={busy}><legend className="sr-only">Investigation fields</legend>
      <label className="field">Title<input required maxLength={120} value={fields.title} onChange={e => setFields({ ...fields, title: e.target.value })} /><span>1–120 characters</span></label>
      <label className="field">Main research question<textarea required minLength={10} maxLength={1000} rows={4} value={fields.question} onChange={e => setFields({ ...fields, question: e.target.value })} /><span>10–1,000 characters. No question is sent to a provider.</span></label>
      <label className="field">Description (optional)<textarea maxLength={5000} rows={3} value={fields.description ?? ''} onChange={e => setFields({ ...fields, description: e.target.value })} /><span>Up to 5,000 characters</span></label>
    </fieldset>
    {error && <p role="alert" className="error-state">{error}</p>}
    <div className="actions"><button className="button primary" disabled={busy || (!!initial && !dirty)}>{busy ? 'Saving details…' : initial ? 'Save details' : 'Create investigation'}</button>{!initial && <Link to="/" className="button secondary">Cancel</Link>}<span role="status">{busy ? 'Saving locally…' : dirty ? 'Unsaved details' : initial ? 'Details saved locally' : 'Not created yet'}</span></div>
  </form>
}
