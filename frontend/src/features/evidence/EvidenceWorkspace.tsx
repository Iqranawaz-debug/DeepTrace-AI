import { useCallback, useEffect, useRef, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { SavedUrls } from './SavedUrls'
import { cancelCollection, getPassages, getPlan, getProviders, getSource, listRuns, listSources, setCollectionConsent, startCollection, type CollectionRun, type Passage, type Providers, type Source } from '../../api/client'

const active = (run: CollectionRun) => ['queued', 'running'].includes(run.status)
export function EvidenceWorkspace({ investigationId }: { investigationId: string }) {
  const [providers, setProviders] = useState<Providers>()
  const [runs, setRuns] = useState<CollectionRun[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [offset, setOffset] = useState(0)
  const [urls, setUrls] = useState('https://fixture.example/article')
  const [accepted, setAccepted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selected, setSelected] = useState<Source>()
  const [passages, setPassages] = useState<Passage[]>([])
  const [inspecting, setInspecting] = useState(false)
  const [open, setOpen] = useState(false)
  const pending = useRef<{ key: string; id: string } | null>(null)
  const refresh = useCallback(async () => {
    const [p, r, s] = await Promise.all([getProviders(), listRuns(investigationId, offset), listSources(investigationId, offset)])
    setProviders(p); setRuns(r); setSources(s)
  }, [investigationId, offset])
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try { if (!stopped && document.visibilityState !== 'hidden') await refresh() }
      catch { if (!stopped) setError('Could not load evidence. Saved sources remain on this computer. Retry when the backend is available.') }
      if (!stopped) timer = setTimeout(poll, 1500)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [refresh])
  async function act(action: () => Promise<void>, message: string) {
    setBusy(true); setError(''); setNotice('')
    try { await action(); setNotice(message); await refresh() }
    catch { setError('The evidence operation could not be confirmed. Your URLs and saved sources are retained. Check the backend and retry; another run or newer plan may need attention.') }
    finally { setBusy(false) }
  }
  async function collect() {
    const entries = urls.split(/\r?\n/).map(url => url.trim()).filter(Boolean)
    if (!entries.length || entries.length > 15 || entries.some(url => !/^https:\/\/fixture\.example\/(article|second|failure|blocked)$/.test(url))) {
      setError('Use 1–15 synthetic URLs, one per line: https://fixture.example/article, /second, /failure or /blocked. Real website collection is disabled.')
      return
    }
    await act(async () => {
      const plan = await getPlan(investigationId)
      const key = JSON.stringify([entries, plan.revision_no])
      if (pending.current?.key !== key) pending.current = { key, id: crypto.randomUUID() }
      await startCollection(investigationId, pending.current.id, entries, plan.revision_no)
      pending.current = null
      setOffset(0)
    }, 'Synthetic collection requested. No website was contacted.')
  }
  async function inspect(source: Source) {
    setSelected(source); setPassages([]); setOpen(true); setInspecting(true)
    try {
      const [saved, parts] = await Promise.all([getSource(source.id, investigationId), getPassages(source.id, investigationId)])
      setSelected(saved); setPassages(parts)
    } catch { setError('Could not open the saved source. Close the inspector and retry.') }
    finally { setInspecting(false) }
  }
  return <section className="evidence-workspace" aria-labelledby="evidence-title">
    <div className="page-intro"><p className="eyebrow">Evidence · Local storage</p><h2 id="evidence-title">Evidence workspace</h2><p>{providers?.live_network ? 'Sources saved by research runs appear below.' : 'Live research is disabled. Mock mode uses clearly labelled synthetic fixtures only; these are not research findings.'}</p></div>
    {error && <div role="alert" className="error-state">{error}<button className="button secondary" onClick={() => void act(refresh, 'Evidence refreshed.')}>Retry evidence</button></div>}
    {notice && <p role="status">{notice}</p>}
    {!providers ? <p role="status">Loading evidence…</p> : !providers.fixture_collection ? <p>{providers.live_network ? 'Manual fixture collection is off in live mode. Use Research above.' : 'Offline mode: saved evidence is available. Collection is disabled.'}</p> : <>
      <p>Fixture disclosure v1: only application-owned sample text is processed and stored locally. No DNS lookup, public website, search service or AI provider is contacted. Revoking permission cancels active collection; saved sources remain.</p>
      {!providers.consent ? <div className="consent-panel"><label><input type="checkbox" checked={accepted} onChange={event => setAccepted(event.target.checked)} /> I understand this is a synthetic demonstration.</label><button className="button secondary" disabled={!accepted || busy} onClick={() => void act(() => setCollectionConsent(true), 'Synthetic fixture permission granted.')}>Enable synthetic collection</button></div> : <button className="button secondary" disabled={busy} onClick={() => void act(() => setCollectionConsent(false), 'Permission revoked. Active collection will stop.')}>Revoke fixture permission</button>}
      <form onSubmit={event => { event.preventDefault(); void collect() }}>
        <label htmlFor="evidence-urls">Synthetic source URLs (one per line)</label>
        <textarea id="evidence-urls" value={urls} maxLength={30735} rows={3} onChange={event => setUrls(event.target.value)} aria-describedby="url-help" />
        <p id="url-help">Try https://fixture.example/article. Up to 15 URLs. The current saved plan is snapshotted for each run.</p>
        <button className="button" disabled={busy || !providers.consent || runs.some(active)}>Collect synthetic evidence</button>
      </form>
    </>}
    <SavedUrls investigationId={investigationId} />
    <h3>Run history</h3>
    {providers && !runs.some(run => (run.scope ?? 'evidence_collection') === 'evidence_collection') && <p>No collection runs yet.</p>}
    <ul className="evidence-list">{runs.filter(run => (run.scope ?? 'evidence_collection') === 'evidence_collection').map(run => <li key={run.id}><strong>SIMULATED · {run.status.replaceAll('_', ' ')}</strong><p>{new Date(run.created_at).toLocaleString()} · Plan revision {run.plan_revision}</p><details><summary>Run snapshot</summary><p>{run.question_snapshot}</p><ul>{run.urls.map(url => <li key={url}>{url}</li>)}</ul><p>Run ID: {run.id}</p></details>{run.error_code && <p>Collection incomplete: {run.error_code.replaceAll('_', ' ')}. Saved sources are retained.</p>}{active(run) && <button className="button secondary" disabled={busy} onClick={() => void act(() => cancelCollection(run.id, investigationId), 'Cancellation requested.')}>Cancel collection</button>}</li>)}</ul>
    <h3>Saved sources</h3>
    {providers && !sources.length && <p>No sources saved. Start a synthetic collection to explore provenance and passages.</p>}
    <ul className="evidence-list">{sources.map(source => <li key={source.id}><strong>{source.origin === 'mock' ? 'SIMULATED · ' : ''}{source.title || 'Source unavailable'}</strong><p>{source.original_url}</p><p>{source.status} · {source.limitation}</p>{source.duplicate_of && <p>Duplicate of saved source {source.duplicate_of}; no new passages created.</p>}<button className="button secondary" onClick={() => void inspect(source)}>Inspect source</button></li>)}</ul>
    <nav aria-label="Evidence pagination"><button className="button secondary" disabled={offset === 0 || busy} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous evidence</button><span> Page {Math.floor(offset / 25) + 1} </span><button className="button secondary" disabled={(runs.length < 25 && sources.length < 25) || busy} onClick={() => setOffset(offset + 25)}>Next evidence</button></nav>
    <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog evidence-inspector"><Dialog.Title>Saved source inspector</Dialog.Title><Dialog.Description>{selected?.origin === 'mock' ? 'Immutable synthetic text' : 'Immutable saved text'} and citation-ready provenance. This is not verified research.</Dialog.Description><Dialog.Close className="button secondary">Close inspector</Dialog.Close>
      {inspecting ? <p role="status">Loading source…</p> : selected && <><h3>{selected.title || 'Unavailable source'}</h3><dl><dt>Original URL</dt><dd>{selected.original_url}</dd><dt>Canonical URL</dt><dd>{selected.canonical_url}</dd><dt>Fetched / extracted (UTC)</dt><dd>{selected.fetched_at || 'Unavailable'} / {selected.extracted_at || 'Unavailable'}</dd><dt>SHA-256 of saved text</dt><dd>{selected.text_sha256 || 'No extracted text'}</dd><dt>Extraction version</dt><dd>{selected.extraction_version || 'Unavailable'}</dd><dt>Author / publication date</dt><dd>{selected.author || 'Unknown'} / {selected.published_at || 'Unknown'}; never inferred.</dd></dl><p>{selected.limitation}</p><h3>Saved text</h3><pre>{selected.extracted_text || 'No text saved for this source.'}</pre><h3>Evidence passages</h3>{passages.map(passage => <article key={passage.id}><h4>{passage.display_id}</h4><p>Offsets {passage.start_offset}–{passage.end_offset} (Unicode code points, end exclusive)</p><blockquote>{passage.text}</blockquote></article>)}{passages.length > 0 && passages.length % 25 === 0 && <button className="button secondary" disabled={busy} onClick={() => void act(async () => setPassages([...passages, ...await getPassages(selected.id, investigationId, passages.length)]), 'Passages loaded.')}>Load more passages</button>}</>}
    </Dialog.Content></Dialog.Portal></Dialog.Root>
  </section>
}

