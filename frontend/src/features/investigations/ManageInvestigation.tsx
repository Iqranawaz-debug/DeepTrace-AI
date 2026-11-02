import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import { ApiError, deleteInvestigation, setArchived, setSensitive, type Investigation } from '../../api/client'

export function ManageInvestigation({ investigation, onChanged }: { investigation: Investigation; onChanged: () => void }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const archived = !!investigation.archived_at
  async function act(work: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await work(); onChanged() }
    catch (failure) { setError(failure instanceof ApiError ? [failure.message, failure.detail].filter(Boolean).join(' ') : 'The change could not be confirmed.') }
    finally { setBusy(false) }
  }
  async function remove() {
    setBusy(true); setError('')
    try { await deleteInvestigation(investigation.id, typed); setOpen(false); void navigate('/') }
    catch (failure) { setError(failure instanceof ApiError ? [failure.message, failure.detail].filter(Boolean).join(' ') : 'Deletion could not be confirmed. Reload to check.') }
    finally { setBusy(false) }
  }
  return <section className="settings-card" aria-labelledby="manage-title"><h2 id="manage-title">Manage</h2>
    <p>Status: <strong>{investigation.lifecycle ?? 'Draft'}</strong></p>
    <label className="check-row"><input type="checkbox" checked={!!investigation.sensitive} disabled={busy} onChange={event => void act(() => setSensitive(investigation.id, event.target.checked))} /> Mark sensitive: never send this investigation’s question or passages to a hosted model</label>
    <div className="actions"><button className="button secondary" disabled={busy} onClick={() => void act(() => setArchived(investigation.id, !archived))}>{archived ? 'Unarchive' : 'Archive'}</button>
      <Dialog.Root open={open} onOpenChange={value => { setOpen(value); setTyped('') }}><Dialog.Trigger asChild><button className="button secondary">Delete investigation</button></Dialog.Trigger>
        <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog"><Dialog.Title>Delete this investigation?</Dialog.Title>
          <Dialog.Description>This permanently removes its plan, sources, passages, drafts and reports from this computer. It can’t be undone. Files you downloaded, upgrade backups in the data folder and OS or cloud backups aren’t affected, and data already sent to a provider can’t be recalled.</Dialog.Description>
          <label className="field">Type the title to confirm: {investigation.title}<input value={typed} onChange={event => setTyped(event.target.value)} /></label>
          {error && <p role="alert" className="error-state">{error}</p>}
          <div className="actions"><Dialog.Close className="button secondary">Keep investigation</Dialog.Close><button className="button primary" disabled={busy || typed !== investigation.title} onClick={() => void remove()}>Delete permanently</button></div></Dialog.Content></Dialog.Portal></Dialog.Root></div>
    {error && !open && <p role="alert" className="error-state">{error}</p>}
  </section>
}
