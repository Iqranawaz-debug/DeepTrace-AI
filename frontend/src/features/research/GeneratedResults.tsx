import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import { generatedDownloadUrl, getGeneratedAnswer, getGeneratedReport, listGeneratedReports, type GeneratedAnswer, type GeneratedClaim, type GeneratedReport, type GeneratedReportSummary } from '../../api/client'
import { ExternalSource } from '../evidence/ExternalSource'
import { locateQuote } from './tracker'

function Check({ ok, text }: { ok: boolean; text: string }) {
  return <li className={ok ? 'check-pass' : 'check-fail'}><span className="sr-only">{ok ? 'Passed: ' : 'Failed: '}</span><span aria-hidden="true">{ok ? '✓' : '✕'}</span> {text}</li>
}

function Passage({ text, quote }: { text: string; quote: string | null }) {
  const range = locateQuote(text, quote)
  if (!range) return <><blockquote>{text}</blockquote>{quote && <p className="record-dates">The exact excerpt couldn't be located. The full passage is shown.</p>}</>
  return <blockquote>{text.slice(0, range[0])}<mark className="cited-excerpt">{text.slice(range[0], range[1])}</mark>{text.slice(range[1])}</blockquote>
}

function EvidenceBody({ answer, position, move, showClaim }: { answer: GeneratedAnswer; position: { claim: number; cite: number }; move: (cite: number) => void; showClaim: (ordinal: number) => void }) {
  const claim: GeneratedClaim = answer.claims[position.claim]
  const citation = claim.citations[position.cite]
  const usable = citation.reference_valid
  const citedBy = answer.claims.filter(other => other.citations.some(item => item.passage_id === citation.passage_id))
  return <>
    <p className="record-dates">Web page · {citation.source_status ?? 'unknown status'}</p>
    <h3>{citation.source_title || 'Untitled source'}</h3>
    {claim.citations.length > 1 && <div className="actions"><span>Citation {position.cite + 1} of {claim.citations.length} for this claim</span>
      <button type="button" className="button secondary" disabled={position.cite === 0} onClick={() => move(position.cite - 1)}>Previous citation<span className="sr-only"> ({position.cite + 1} of {claim.citations.length})</span></button>
      <button type="button" className="button secondary" disabled={position.cite === claim.citations.length - 1} onClick={() => move(position.cite + 1)}>Next citation<span className="sr-only"> ({position.cite + 1} of {claim.citations.length})</span></button></div>}
    <ExternalSource url={citation.original_url} />
    {usable ? <Passage text={citation.passage_text} quote={citation.quoted_text} /> : <p role="alert" className="error-state">This reference couldn't be confirmed, so it isn't shown as evidence.</p>}
    <dl><dt>Retrieved (UTC)</dt><dd>{citation.fetched_at || 'Unavailable'}</dd><dt>Location</dt><dd>Characters {citation.start_offset}–{citation.end_offset} of the saved text</dd></dl>
    <h4>Automatic checks</h4>
    <ul className="check-list">
      <Check ok={usable} text="Passage found in saved sources" />
      <Check ok={usable} text="Belongs to this investigation" />
      {citation.quote_valid === null ? <li>No quotation presented</li> : <Check ok={citation.quote_valid} text="Quotation matches saved text" />}
    </ul>
    <p>These checks confirm the reference and wording. They don't confirm the claim is true.</p>
    <p className="record-dates">Semantic assessment isn't performed in this version, so a valid citation here doesn't show that the source supports the claim.</p>
    <h4>Cited by</h4>
    <ul className="cited-by">{citedBy.map(other => <li key={other.ordinal}><button type="button" className="link-button" onClick={() => showClaim(other.ordinal)}>Finding {other.ordinal}: {other.claim_text}</button></li>)}</ul>
  </>
}

/** Model and source text render only as React text: nothing here can execute or load remotely. */
export function GeneratedResults({ investigationId }: { investigationId: string }) {
  const [params, setParams] = useSearchParams()
  const [answer, setAnswer] = useState<GeneratedAnswer | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [versions, setVersions] = useState<GeneratedReportSummary[]>([])
  const [selected, setSelected] = useState<number>()
  const [report, setReport] = useState<GeneratedReport>()
  const [error, setError] = useState('')
  const [chosen, setChosen] = useState<{ claim: number; cite: number }>()
  const opener = useRef<HTMLElement | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    let active = true
    Promise.all([getGeneratedAnswer(investigationId), listGeneratedReports(investigationId)]).then(([a, r]) => { if (active) { setAnswer(a); setVersions(r); setLoaded(true) } }).catch(() => { if (active) setError('Could not load saved results. Nothing was changed.') })
    return () => { active = false }
  }, [investigationId])
  const version = selected ?? versions[0]?.version_no
  useEffect(() => {
    let active = true
    if (version) getGeneratedReport(investigationId, version).then(value => { if (active) setReport(value) }).catch(() => { if (active) setError('This report version could not be opened or failed its integrity check.') })
    return () => { active = false }
  }, [investigationId, version])
  // The drawer's open state lives in ?evidence= so refresh, Back and shared local links work.
  const evidence = params.get('evidence')
  function resolve() {
    if (!evidence || !answer) return undefined
    if (chosen && answer.claims[chosen.claim]?.citations[chosen.cite]?.passage_id === evidence) return chosen
    for (const [claim, item] of answer.claims.entries()) {
      const cite = item.citations.findIndex(citation => citation.passage_id === evidence)
      if (cite >= 0) return { claim, cite }
    }
    return undefined
  }
  const position = resolve()
  function setEvidence(id: string | null) {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (id) next.set('evidence', id); else next.delete('evidence')
      return next
    })
  }
  function close() { setChosen(undefined); setEvidence(null) }
  function showClaim(ordinal: number) {
    close()
    window.setTimeout(() => { const target = document.getElementById(`finding-${ordinal}`); target?.scrollIntoView({ block: 'center' }); target?.focus() }, 0)
    opener.current = null
  }
  if (error) return <p role="alert" className="error-state">{error}</p>
  if (!loaded || (!answer && !versions.length)) return null
  return <div className="generated-results">
    {answer && <section aria-labelledby="answer-title"><h3 id="answer-title">Findings</h3>
      <p className="mode-note"><strong>{answer.mode === 'mock' ? 'SIMULATED · Not real research. ' : ''}AI-generated research aid. Verify important findings using original sources.</strong> {answer.provider_id === 'none' ? 'This partial report used no language model.' : `Generated by ${answer.provider_id} (${answer.model_id}), prompt ${answer.prompt_version}.`}</p>
      <p>{answer.summary_text}</p>
      {answer.suppressed_citations > 0 && <p className="mode-note">{answer.suppressed_citations} citation(s) failed validation and were suppressed.</p>}
      {answer.claims.length === 0 ? <p>No findings were produced.</p> : <ol className="claim-list">{answer.claims.map((claim, index) => <li key={claim.ordinal} id={`finding-${claim.ordinal}`} tabIndex={-1}><span className={claim.evidence_state === 'cited' ? 'badge-cited' : 'badge-missing'}>{claim.evidence_state === 'cited' ? 'Cited' : 'Not established'}</span><p>{claim.claim_text}</p>{claim.explanation && <p className="record-dates">{claim.explanation}</p>}{claim.citations.length > 0 && <div className="actions">{claim.citations.map((citation, cite) => <button key={citation.passage_id} type="button" className="button secondary citation-chip" aria-label={`Open evidence ${citation.display_id}`} onClick={event => { opener.current = event.currentTarget; setChosen({ claim: index, cite }); setEvidence(citation.passage_id) }}>{citation.display_id}</button>)}</div>}</li>)}</ol>}
      {answer.limitations_text && <><h4>Limitations</h4><p>{answer.limitations_text}</p></>}
      {answer.needed_evidence_text && <><h4>Evidence still needed</h4><p>{answer.needed_evidence_text}</p></>}
    </section>}
    <Dialog.Root open={!!evidence} onOpenChange={value => { if (!value) close() }}><Dialog.Portal><Dialog.Overlay className="scrim" />
      <Dialog.Content className="unsaved-dialog evidence-inspector" onOpenAutoFocus={event => { event.preventDefault(); heading.current?.focus() }} onCloseAutoFocus={event => { if (opener.current) { event.preventDefault(); opener.current.focus() } }}>
        <Dialog.Title asChild><h2 ref={heading} tabIndex={-1}>Evidence{position && answer ? ` ${answer.claims[position.claim].citations[position.cite].display_id}` : ''}</h2></Dialog.Title>
        <Dialog.Description>What was saved from the source, and what the software checked.</Dialog.Description>
        {position && answer ? <EvidenceBody answer={answer} position={position} move={cite => { const next = { claim: position.claim, cite }; setChosen(next); setEvidence(answer.claims[position.claim].citations[cite].passage_id); heading.current?.focus() }} showClaim={showClaim} /> : <p role="alert" className="error-state">This passage isn't available in this investigation.</p>}
        <Dialog.Close className="button secondary">Close evidence</Dialog.Close>
      </Dialog.Content></Dialog.Portal></Dialog.Root>
    {versions.length > 0 && <section aria-labelledby="generated-report-title"><h3 id="generated-report-title">Research report</h3>
      <label className="field">Report version<select value={version} onChange={event => setSelected(Number(event.target.value))}>{versions.map(item => <option key={item.version_no} value={item.version_no}>Version {item.version_no} — {new Date(item.created_at).toLocaleString()}</option>)}</select></label>
      {report && report.version_no === version && <article aria-label={`Research report version ${report.version_no}`}>
        {report.current_warnings.map(warning => <p key={warning} role="note" className="mode-note">{warning}</p>)}
        <p role="status">Report checked: {report.validation_summary.citations} references found, {report.validation_summary.quotations_matched} quotations match. {report.validation_summary.claims_not_established} claims are marked not established.</p>
        <p className="record-dates mono hash">SHA-256 {report.markdown_sha256}</p>
        <a className="button secondary" href={generatedDownloadUrl(investigationId, report.version_no)} download>Download report (.md)</a>
        <h4>Exact file contents</h4><pre className="report-preview" tabIndex={0}>{report.markdown_text}</pre>
      </article>}
    </section>}
  </div>
}
