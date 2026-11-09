import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import {
  ANSWER_FIELDS, ApiError, createReport, getAnswer, getReport, listEvidencePassages, listNotes, listReports, reportDownloadUrl, saveAnswer, saveNote,
  type Answer, type AnswerField, type Citation, type ClaimDraft, type ClaimType, type EvidenceNote, type EvidencePassage, type Investigation, type Plan, type Relation, type ReportSummary, type ReportVersion, type Stance,
} from '../../api/client'
import { useUnsaved } from '../investigations/InvestigationForm'
import { GeneratedReportViewer } from '../research/GeneratedResults'
import { useWorkspace } from '../workspace/workspace'

const STANCES: Record<Stance, string> = { unreviewed: 'Not yet reviewed', supports: 'Supports (my judgment)', contradicts: 'Contradicts (my judgment)', context: 'Context only', insufficient: 'Insufficient for this question' }
const RELATIONS: Record<Relation, string> = { supports: 'Supports the claim', contradicts: 'Contradicts the claim', context: 'Context' }
const CLAIM_TYPES: Record<ClaimType, string> = { finding: 'Finding (needs supporting citation)', interpretation: 'Interpretation', conflict: 'Conflicting evidence', hypothesis: 'Unsupported hypothesis', gap: 'Missing evidence', conclusion: 'My conclusion' }
const FIELD_LABELS: Record<AnswerField, [string, number]> = { scope_text: ['Scope', 5000], methodology_text: ['Methodology notes', 5000], summary_text: ['Summary', 10000], limitations_text: ['Limitations and uncertainty', 5000], next_steps_text: ['Unanswered questions and next steps', 5000] }
const message = (error: unknown) => error instanceof ApiError ? [error.message, error.detail].filter(Boolean).join(' ') : 'The local request failed. Your edits are still here.'
const fieldsOf = (answer: Answer) => Object.fromEntries(ANSWER_FIELDS.map(key => [key, answer[key] ?? ''])) as Record<AnswerField, string>
const draftsOf = (answer: Answer): ClaimDraft[] => answer.claims.map(claim => ({ id: claim.id, claim_type: claim.claim_type, claim_text: claim.claim_text, citations: claim.citations.map(c => ({ passage_id: c.passage_id, relation: c.relation, quoted_text: c.quoted_text })) }))

async function loadPassages(id: string) {
  // Bounded: at most four pages of 50 passages are offered for review and citation.
  const passages: EvidencePassage[] = []
  for (let offset = 0; offset < 200; offset += 50) { const page = await listEvidencePassages(id, offset); passages.push(...page); if (page.length < 50) break }
  return passages
}

export function ReportTab() {
  const { id, research } = useWorkspace()
  const [data, setData] = useState<{ passages: EvidencePassage[]; answer: Answer }>()
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    Promise.all([loadPassages(id), getAnswer(id)]).then(([passages, answer]) => { if (active) setData({ passages, answer }) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, attempt, research.resultKey])
  return <>
    <div className="panel-intro"><h2>Report</h2>
      <p>Research runs save an AI-generated report here. In your own draft, you write every claim and classification. DeepTrace checks only that each citation points to a saved passage in this investigation and that quotations match the saved text. It does not judge whether a passage supports a claim, and no AI model touches your draft.</p></div>
    <section className="card" aria-labelledby="generated-report-title"><div className="card-head"><h2 id="generated-report-title">Research report</h2><span className="chip">AI-generated</span></div>
      <GeneratedReportViewer key={research.resultKey} investigationId={id} /></section>
    {error ? <div role="alert" className="error-state">Could not open your report draft. Saved work is unchanged.<button className="button secondary" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Retry report</button></div>
      : !data ? <p role="status">Loading report draft…</p> : <>
        {data.passages.some(p => p.source_origin === 'mock') && <p className="mode-note"><strong>Simulated evidence.</strong> Passages come from synthetic fixtures and support no conclusions about the world.</p>}
        <DraftEditor investigationId={id} answer={data.answer} passages={data.passages} onSaved={saved => setData(current => current && { ...current, answer: saved })} />
        <Versions investigationId={id} answer={data.answer} />
      </>}
  </>
}

export function EvidenceReviewSection({ refresh = 0 }: { refresh?: number }) {
  const { id, investigation, plan, research } = useWorkspace()
  const [data, setData] = useState<{ passages: EvidencePassage[]; notes: EvidenceNote[] }>()
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    Promise.all([loadPassages(id), listNotes(id)]).then(([passages, notes]) => { if (active) setData({ passages, notes }) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id, attempt, research.resultKey, refresh])
  if (error) return <div role="alert" className="error-state">Could not load saved passages. Saved work is unchanged.<button className="button secondary" onClick={() => { setError(false); setAttempt(attempt + 1) }}>Retry evidence review</button></div>
  if (!data) return <p role="status">Loading evidence review…</p>
  return <EvidenceReview investigationId={id} data={{ investigation, plan, ...data }} onNotes={notes => setData({ ...data, notes })} />
}

function PassageButton({ citation }: { citation: Citation }) {
  return <Dialog.Root><Dialog.Trigger asChild><button type="button" className="button secondary citation-chip" aria-label={`Open passage ${citation.display_id}`}>{citation.display_id}</button></Dialog.Trigger>
    <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="unsaved-dialog evidence-inspector"><Dialog.Title>Evidence {citation.display_id}</Dialog.Title>
      <Dialog.Description>Saved passage text. A valid reference does not show that the source supports the claim.</Dialog.Description>
      <dl><dt>Source</dt><dd>{citation.source_title || 'Untitled source'}</dd><dt>Location</dt><dd>Characters {citation.start_offset}–{citation.end_offset} of the saved extracted text (Unicode code points, end exclusive)</dd>
        <dt>Checks</dt><dd>Reference: {citation.reference_valid ? 'passage found in this investigation' : `invalid (${citation.invalid_reason ?? 'unknown'})`}. Quotation: {citation.quote_valid === null ? 'none presented' : citation.quote_valid ? 'matches saved text' : 'does not match'}.</dd></dl>
      <blockquote>{citation.passage_text}</blockquote><Dialog.Close className="button secondary">Close passage</Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root>
}

function EvidenceReview({ investigationId, data, onNotes }: { investigationId: string; data: { investigation: Investigation; plan: Plan; passages: EvidencePassage[]; notes: EvidenceNote[] }; onNotes: (notes: EvidenceNote[]) => void }) {
  const targets: [string, string][] = [['question', `Main question: ${data.investigation.question}`], ...data.plan.items.map((item, index): [string, string] => [item.id, `Step ${index + 1}: ${item.sub_question}`])]
  const unreviewed = data.passages.filter(p => !data.notes.some(n => n.passage_id === p.id && n.stance !== 'unreviewed')).length
  return <section className="card" aria-labelledby="review-title"><h2 id="review-title">Evidence review</h2>
    <p>Link saved passages to the question or plan steps and record your judgment. Classifications are yours, not verified facts. {unreviewed} of {data.passages.length} passages have no review yet.</p>
    {!data.passages.length && <p>No usable passages are saved. Run research or collect sources first; saved URLs are not evidence.</p>}
    <ol className="evidence-list">{data.passages.map(passage => <li key={passage.id}><h3>{passage.display_id} · {passage.source_title || 'Untitled source'}</h3>
      <p className="record-dates">{passage.source_origin === 'mock' ? 'SIMULATED · ' : ''}{passage.source_status} · characters {passage.start_offset}–{passage.end_offset}</p>
      <blockquote>{passage.text}</blockquote>
      {data.notes.filter(n => n.passage_id === passage.id).map(note => <NoteForm key={note.id} investigationId={investigationId} passage={passage} targets={targets} existing={note} onSaved={saved => onNotes(data.notes.map(n => n.id === saved.id ? saved : n))} />)}
      <NoteForm key={`new-${data.notes.filter(n => n.passage_id === passage.id).length}`} investigationId={investigationId} passage={passage} targets={targets.filter(([key]) => !data.notes.some(n => n.passage_id === passage.id && n.target_key === key))} onSaved={saved => onNotes([...data.notes, saved])} />
    </li>)}</ol></section>
}

function NoteForm({ investigationId, passage, targets, existing, onSaved }: { investigationId: string; passage: EvidencePassage; targets: [string, string][]; existing?: EvidenceNote; onSaved: (note: EvidenceNote) => void }) {
  const [target, setTarget] = useState(existing?.target_key ?? targets[0]?.[0] ?? '')
  const [stance, setStance] = useState<Stance>(existing?.stance ?? 'unreviewed')
  const [note, setNote] = useState(existing?.note ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [key] = useState(() => existing?.id ?? crypto.randomUUID())
  if (!existing && !targets.length) return null
  const label = existing ? `${passage.display_id} for ${existing.target_label}` : `new review of ${passage.display_id}`
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError('')
    try { onSaved(await saveNote(investigationId, { id: key, passage_id: passage.id, target_key: existing?.target_key ?? target, stance, note: note.trim() || null, expected_revision: existing?.revision_no ?? 0 })) }
    catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  return <form className="note-form" onSubmit={submit} aria-label={existing ? `Review: ${label}` : `Add review for ${passage.display_id}`}>
    {existing ? <p><strong>For:</strong> {existing.target_label}{!existing.target_current && ' (plan step removed; label kept as saved)'}</p>
      : <label className="field">Relates to<select value={target} onChange={e => setTarget(e.target.value)}>{targets.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>}
    <label className="field">My classification<select value={stance} onChange={e => setStance(e.target.value as Stance)}>{Object.entries(STANCES).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
    <label className="field">My note (optional)<textarea rows={2} maxLength={5000} value={note} onChange={e => setNote(e.target.value)} /><span>Your words, kept separate from the source text</span></label>
    <div className="actions"><button className="button secondary" disabled={busy}>{busy ? 'Saving review…' : existing ? 'Update review' : 'Add review'}</button>{existing && <span role="status">Saved · revision {existing.revision_no}</span>}</div>
    {error && <p role="alert" className="error-state">{error}</p>}
  </form>
}

function DraftEditor({ investigationId, answer, passages, onSaved }: { investigationId: string; answer: Answer; passages: EvidencePassage[]; onSaved: (answer: Answer) => void }) {
  const [fields, setFields] = useState(() => fieldsOf(answer))
  const [claims, setClaims] = useState(() => draftsOf(answer))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [announcement, setAnnouncement] = useState('')
  const dirty = JSON.stringify([fields, claims]) !== JSON.stringify([fieldsOf(answer), draftsOf(answer)])
  const clearDirty = useUnsaved(dirty, busy)
  const saved = new Map(answer.claims.map(claim => [claim.id, claim]))
  const update = (index: number, change: Partial<ClaimDraft>) => setClaims(claims.map((claim, i) => i === index ? { ...claim, ...change } : claim))
  function move(index: number, direction: number) {
    const next = [...claims]; const target = index + direction
    ;[next[index], next[target]] = [next[target], next[index]]
    setClaims(next); setAnnouncement(`Moved claim to position ${target + 1} of ${claims.length}. Save the draft to apply.`)
  }
  async function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError('')
    try {
      const result = await saveAnswer(investigationId, Object.fromEntries(ANSWER_FIELDS.map(key => [key, fields[key].trim() || null])) as Record<AnswerField, string | null>, claims.map(c => ({ ...c, citations: c.citations.map(r => ({ ...r, quoted_text: r.quoted_text?.trim() || null })) })), answer.revision_no)
      clearDirty(); setFields(fieldsOf(result)); setClaims(draftsOf(result)); onSaved(result); setAnnouncement(`Draft saved · revision ${result.revision_no}`)
    } catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  return <form className="card" onSubmit={submit} aria-labelledby="draft-title"><h2 id="draft-title">Report draft</h2>
    <p>Everything here is your own text. A finding counts as <strong>Cited</strong> only when it has at least one valid citation marked as supporting; otherwise it is shown as <strong>Not established</strong>. Invalid citations are rejected, never silently removed.</p>
    <fieldset disabled={busy}><legend className="sr-only">Report sections</legend>
      {ANSWER_FIELDS.map(key => <label key={key} className="field">{FIELD_LABELS[key][0]}<textarea rows={3} maxLength={FIELD_LABELS[key][1]} value={fields[key]} onChange={e => setFields({ ...fields, [key]: e.target.value })} /><span>Up to {FIELD_LABELS[key][1].toLocaleString()} characters</span></label>)}
      <h3>Claims</h3>{!claims.length && <p>No claims yet. A report without claims presents no findings.</p>}
      <ol className="plan-list">{claims.map((claim, index) => { const stored = saved.get(claim.id); return <li key={claim.id} className="plan-step"><h4>Claim {index + 1}{stored && !dirty && <> · <span className={stored.evidence_state === 'cited' ? 'badge-cited' : 'badge-missing'}>{stored.evidence_state === 'cited' ? 'Cited' : 'Not established'}</span></>}</h4>
        <label className="field">Claim type {index + 1}<select value={claim.claim_type} onChange={e => update(index, { claim_type: e.target.value as ClaimType })}>{Object.entries(CLAIM_TYPES).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
        <label className="field">Claim text {index + 1}<textarea required rows={2} maxLength={2000} value={claim.claim_text} onChange={e => update(index, { claim_text: e.target.value })} /><span>1–2,000 characters</span></label>
        {claim.citations.map((cite, ci) => <fieldset key={cite.passage_id + ci} className="citation-row"><legend>Citation {ci + 1} for claim {index + 1}</legend>
          <label className="field">Passage<select value={cite.passage_id} onChange={e => update(index, { citations: claim.citations.map((c, j) => j === ci ? { ...c, passage_id: e.target.value } : c) })}>{passages.map(p => <option key={p.id} value={p.id}>{p.display_id} · {p.source_title || 'Untitled source'}</option>)}</select></label>
          <label className="field">Relation<select value={cite.relation} onChange={e => update(index, { citations: claim.citations.map((c, j) => j === ci ? { ...c, relation: e.target.value as Relation } : c) })}>{Object.entries(RELATIONS).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
          <label className="field">Exact quotation (optional)<textarea rows={2} maxLength={2000} value={cite.quoted_text ?? ''} onChange={e => update(index, { citations: claim.citations.map((c, j) => j === ci ? { ...c, quoted_text: e.target.value } : c) })} /><span>Must appear in the passage; case-sensitive, spacing ignored</span></label>
          {stored && !dirty && stored.citations[ci] && <p className="record-dates"><PassageButton citation={stored.citations[ci]} /> {stored.citations[ci].reference_valid ? 'Reference valid' : 'Reference invalid'}{stored.citations[ci].quote_valid !== null && ` · quotation ${stored.citations[ci].quote_valid ? 'matches' : 'does not match'}`}</p>}
          <button type="button" className="button secondary" aria-label={`Remove citation ${ci + 1} from claim ${index + 1}`} onClick={() => update(index, { citations: claim.citations.filter((_, j) => j !== ci) })}>Remove citation</button></fieldset>)}
        <div className="actions"><button type="button" className="button secondary" disabled={claim.citations.length >= Math.min(10, passages.length)} aria-label={`Add citation to claim ${index + 1}`} onClick={() => { const unused = passages.find(p => !claim.citations.some(c => c.passage_id === p.id)); if (unused) update(index, { citations: [...claim.citations, { passage_id: unused.id, relation: 'supports', quoted_text: null }] }) }}>Add citation</button>
          <button type="button" className="button secondary" disabled={index === 0} aria-label={`Move up claim ${index + 1}`} onClick={() => move(index, -1)}>Move up</button>
          <button type="button" className="button secondary" disabled={index === claims.length - 1} aria-label={`Move down claim ${index + 1}`} onClick={() => move(index, 1)}>Move down</button>
          <button type="button" className="button secondary" aria-label={`Remove claim ${index + 1}`} onClick={() => { setClaims(claims.filter((_, i) => i !== index)); setAnnouncement(`Removed claim ${index + 1}. Save the draft to apply.`) }}>Remove claim</button></div>
      </li> })}</ol>
      <button type="button" className="button secondary" disabled={claims.length >= 30} onClick={() => setClaims([...claims, { id: crypto.randomUUID(), claim_type: 'finding', claim_text: '', citations: [] }])}>Add claim</button>
    </fieldset>
    <p role="status">{announcement}</p>{error && <p role="alert" className="error-state">{error}</p>}
    <div className="actions"><button className="button primary" disabled={busy || (!dirty && answer.revision_no > 0)}>{busy ? 'Saving draft…' : 'Save draft'}</button><span role="status">{busy ? 'Saving locally…' : dirty ? 'Unsaved draft changes' : answer.revision_no ? `Draft saved locally · revision ${answer.revision_no}` : 'Draft not saved yet'}</span></div>
  </form>
}

function Versions({ investigationId, answer }: { investigationId: string; answer: Answer }) {
  const [params, setParams] = useSearchParams()
  const [versions, setVersions] = useState<ReportSummary[]>()
  const [current, setCurrent] = useState<ReportVersion>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const selected = Number(params.get('version')) || versions?.[0]?.version_no
  const refresh = useCallback(async () => setVersions(await listReports(investigationId)), [investigationId])
  useEffect(() => {
    let active = true
    listReports(investigationId).then(rows => { if (active) setVersions(rows) }).catch(() => { if (active) setError('Could not load report versions.') })
    return () => { active = false }
  }, [investigationId])
  useEffect(() => {
    let active = true
    if (selected) getReport(investigationId, selected).then(v => { if (active) setCurrent(v) }).catch(() => { if (active) setError('This report version could not be opened. Saved versions are unchanged.') })
    return () => { active = false }
  }, [investigationId, selected, answer.revision_no])
  async function create() {
    setBusy(true); setError('')
    try { const created = await createReport(investigationId, answer.revision_no); await refresh(); setParams({ version: String(created.version_no) }) }
    catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  return <section className="card" aria-labelledby="versions-title"><h2 id="versions-title">Report versions</h2>
      <p>Creating a version re-checks every citation and saves an immutable Markdown snapshot of the saved draft. Saving does not make a report verified or complete.</p>
      <div className="actions"><button className="button primary" disabled={busy || answer.revision_no === 0} onClick={() => void create()}>{busy ? 'Checking references…' : 'Create report version'}</button>{answer.revision_no === 0 && <span>Save the draft first.</span>}</div>
      {error && <p role="alert" className="error-state">{error}</p>}
      {!versions ? <p role="status">Loading versions…</p> : !versions.length ? <p>No report versions yet.</p> : <>
        <label className="field">Version<select value={selected} onChange={e => setParams({ version: e.target.value })}>{versions.map(v => <option key={v.version_no} value={v.version_no}>Version {v.version_no} — {new Date(v.created_at).toLocaleString()}</option>)}</select></label>
        {current && current.version_no === selected && <article aria-label={`Report version ${current.version_no} preview`}>
          {current.current_warnings.map(w => <p key={w} role="note" className="mode-note">{w}</p>)}
          <p role="status">Report checked: {current.validation_summary.citations_reference_valid} of {current.validation_summary.citations} references valid, {current.validation_summary.quotations_matched} of {current.validation_summary.quotations} quotations match. {current.validation_summary.claims_not_established} claims are not established.</p>
          <p className="record-dates mono hash">SHA-256 {current.markdown_sha256}</p>
          <a className="button secondary" href={reportDownloadUrl(investigationId, current.version_no)} download>Download Markdown (.md)</a>
          <h3>Exact file contents</h3><pre className="report-preview" tabIndex={0}>{current.markdown_text}</pre>
        </article>}
      </>}
    </section>
}
