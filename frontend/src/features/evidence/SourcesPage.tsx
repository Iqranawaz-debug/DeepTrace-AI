import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPassages, getSource, listSources, type Passage, type Source } from '../../api/client'
import { InvestigationNav } from '../investigations/InvestigationNav'

const FILTERS: [string, string, (status: string) => boolean][] = [
  ['all', 'All', () => true],
  ['fetched', 'Fetched', status => status === 'fetched'],
  ['partial', 'Partial', status => status === 'partial'],
  ['not', 'Not retrieved', status => ['blocked', 'paywalled', 'failed', 'unsupported'].includes(status)],
  ['duplicate', 'Duplicate', status => status === 'duplicate'],
]
const MEANING: Record<string, string> = {
  fetched: 'Text saved', partial: 'Only part of the page could be read', blocked: 'Refused or disallowed; nothing saved. DeepTrace doesn’t bypass access controls.',
  paywalled: 'Behind a paywall; nothing saved', failed: 'Could not retrieve. Other sources weren’t affected.', duplicate: 'Same content as another source', unsupported: 'Content type not supported',
}
const domain = (url: string) => { try { return new URL(url).hostname } catch { return url } }

function SourceRow({ source, investigationId }: { source: Source; investigationId: string }) {
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<{ source: Source; passages: Passage[] }>()
  const [error, setError] = useState(false)
  function toggle() {
    setOpen(!open)
    if (!detail) Promise.all([getSource(source.id, investigationId), getPassages(source.id, investigationId)]).then(([saved, passages]) => setDetail({ source: saved, passages })).catch(() => setError(true))
  }
  const panel = `source-${source.id}`
  return <li className="settings-card"><div className="list-header"><h3>{source.origin === 'mock' ? 'SIMULATED · ' : ''}{source.title || 'Untitled source'}</h3><span className="label">{source.status}</span></div>
    <p className="mono hash">{domain(source.original_url)}</p><p>{MEANING[source.status] ?? source.status}</p>
    <p className="record-dates">Retrieved {source.fetched_at ? new Date(source.fetched_at).toLocaleString() : 'not retrieved'}</p>
    <button className="button secondary" aria-expanded={open} aria-controls={panel} onClick={toggle}>{open ? 'Hide details' : 'Show details'}<span className="sr-only"> for {source.title || 'untitled source'}</span></button>
    {open && <div id={panel}>{error ? <p role="alert" className="error-state">Could not open this source. Saved data is unchanged.</p> : !detail ? <p role="status">Loading source…</p> : <>
      <dl><dt>Original URL</dt><dd className="mono hash">{detail.source.original_url}</dd><dt>Canonical URL</dt><dd className="mono hash">{detail.source.canonical_url}</dd><dt>Author</dt><dd>{detail.source.author || 'Unknown'}</dd><dt>Published</dt><dd>{detail.source.published_at || 'Unknown'}</dd><dt>Extraction version</dt><dd>{detail.source.extraction_version || 'None'}</dd><dt>SHA-256 of saved text</dt><dd className="mono hash">{detail.source.text_sha256 || 'No text saved'}</dd>{detail.source.limitation && <><dt>Limitation</dt><dd>{detail.source.limitation}</dd></>}</dl>
      {detail.passages.map(passage => <article key={passage.id}><h4>{passage.display_id}</h4><blockquote>{passage.text}</blockquote></article>)}</>}</div>}
  </li>
}

export function SourcesPage() {
  const { id = '' } = useParams()
  const [sources, setSources] = useState<Source[]>()
  const [offset, setOffset] = useState(0)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    listSources(id, offset).then(rows => { if (active) { setSources(rows); setError(false) } }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, offset, attempt])
  const test = FILTERS.find(([key]) => key === filter)?.[2] ?? (() => true)
  const shown = sources?.filter(source => test(source.status)) ?? []
  const count = (key: string) => sources?.filter(source => FILTERS.find(([name]) => name === key)?.[2](source.status)).length ?? 0
  return <><div className="page-intro"><p className="eyebrow">Sources · Stored on this computer</p><h1 tabIndex={-1}>Sources</h1>
    <p>Every source considered, including those that couldn’t be read. Saved URLs that were never retrieved are listed in the workspace, not here.</p></div>
    <InvestigationNav id={id} current="sources" />
    {error ? <div role="alert" className="error-state">Could not load sources. Saved data is unchanged.<button className="button secondary" onClick={() => setAttempt(attempt + 1)}>Retry sources</button></div> : !sources ? <p role="status">Loading sources…</p> : <>
      <p>{sources.length} source(s) on this page · {count('fetched')} fetched · {count('partial')} partial · {count('not')} not retrieved · {count('duplicate')} duplicate</p>
      <label className="field">Show<select value={filter} onChange={event => setFilter(event.target.value)}>{FILTERS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      {!shown.length ? <p>{sources.length ? 'No sources match this filter.' : 'No sources yet. Start research from the workspace.'}</p> : <ul className="provider-list">{shown.map(source => <SourceRow key={source.id} source={source} investigationId={id} />)}</ul>}
      <div className="actions"><button className="button secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous sources</button><button className="button secondary" disabled={sources.length < 25} onClick={() => setOffset(offset + 25)}>Next sources</button></div></>}
  </>
}
