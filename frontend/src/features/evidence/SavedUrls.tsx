import { useEffect, useRef, useState } from 'react'
import { ApiError, listSavedUrls, saveUrl, type SavedUrl } from '../../api/client'

/** Manual URL leads. Saving records the address only: nothing is fetched and nothing becomes evidence. */
export function SavedUrls({ investigationId }: { investigationId: string }) {
  const [items, setItems] = useState<SavedUrl[]>()
  const [url, setUrl] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const pending = useRef<{ key: string; id: string } | null>(null)
  useEffect(() => {
    let active = true
    listSavedUrls(investigationId).then(rows => { if (active) setItems(rows) }).catch(() => { if (active) setError('Could not load saved URLs. Retry after the backend is available.') })
    return () => { active = false }
  }, [investigationId])
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError(''); setStatus('')
    const key = JSON.stringify([url.trim(), note.trim()])
    // Keep one identifier per unchanged input so a retried request stays idempotent.
    if (pending.current?.key !== key) pending.current = { key, id: crypto.randomUUID() }
    try {
      const saved = await saveUrl(investigationId, pending.current.id, url.trim(), note.trim() || null)
      pending.current = null
      setItems(current => [saved, ...(current ?? []).filter(item => item.id !== saved.id)])
      setUrl(''); setNote(''); setStatus('URL saved. It has not been retrieved.')
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 409 && failure.detail ? failure.detail : failure instanceof ApiError && failure.status === 422 ? 'Use a public http or https address without credentials. Local and private addresses are refused.' : 'The URL was not saved. Your input is still here. Retry when the backend is available.')
    } finally { setBusy(false) }
  }
  return <section className="settings-card" aria-labelledby="saved-urls-title">
    <h3 id="saved-urls-title">Saved URLs (not retrieved)</h3>
    <p>Keep addresses to read later. DeepTrace does not contact these sites; saved URLs are not sources, evidence or citations.</p>
    <form onSubmit={submit}>
      <label className="field">URL<input value={url} maxLength={2048} required inputMode="url" onChange={event => setUrl(event.target.value)} /><span>http or https; up to 2,048 characters</span></label>
      <label className="field">Note (optional)<input value={note} maxLength={1000} onChange={event => setNote(event.target.value)} /><span>Up to 1,000 characters</span></label>
      <div className="actions"><button className="button secondary" disabled={busy || !url.trim()}>{busy ? 'Saving URL…' : 'Save URL for later'}</button><span role="status">{status}</span></div>
    </form>
    {error && <p role="alert" className="error-state">{error}</p>}
    {!items ? <p role="status">Loading saved URLs…</p> : !items.length ? <p>No URLs saved.</p> :
      <ul className="evidence-list">{items.map(item => <li key={item.id}><strong>Saved · not retrieved</strong><p className="mono">{item.canonical_url}</p>{item.note && <p>{item.note}</p>}<p className="record-dates">Saved {new Date(item.created_at).toLocaleString()}</p></li>)}</ul>}
  </section>
}
