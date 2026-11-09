import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { FileSearch, X } from 'lucide-react'
import { EvidenceBody } from '../research/GeneratedResults'
import { resolvePosition } from '../research/tracker'
import { useWorkspace } from './workspace'

/** Right-hand panel. Its open state lives in ?evidence= so refresh, Back and local links work. */
export function EvidenceInspector() {
  const { id, research, openerRef } = useWorkspace()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const heading = useRef<HTMLHeadingElement>(null)
  const evidence = params.get('evidence')
  const position = resolvePosition(research.answer, evidence, params.get('finding'))
  const citation = position && research.answer?.claims[position.claim].citations[position.cite]
  useEffect(() => { if (evidence) heading.current?.focus() }, [evidence])
  function close() {
    setParams(previous => { const next = new URLSearchParams(previous); next.delete('evidence'); next.delete('finding'); return next })
    const target = openerRef.current
    window.setTimeout(() => { if (target?.isConnected) target.focus() }, 0)
  }
  function showClaim(ordinal: number) {
    openerRef.current = null
    void Promise.resolve(navigate(`/investigations/${encodeURIComponent(id)}/findings`)).then(() => {
      window.setTimeout(() => { const target = document.getElementById(`finding-${ordinal}`); target?.scrollIntoView({ block: 'center' }); target?.focus() }, 0)
    })
  }
  if (!evidence) return <aside className="ws-inspector empty" aria-label="Evidence inspector">
    <FileSearch size={28} strokeWidth={1.5} aria-hidden="true" />
    <h2>Evidence inspector</h2>
    <p>Select a citation such as <span className="mono">P-0001</span> in Findings to see the saved passage, its source and the automatic checks.</p>
  </aside>
  return <aside className="ws-inspector open" aria-labelledby="inspector-title" onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); close() } }}>
    <div className="inspector-head">
      <h2 id="inspector-title" ref={heading} tabIndex={-1}>Evidence{citation ? ` ${citation.display_id}` : ''}</h2>
      <button type="button" className="icon-button small" aria-label="Close evidence" onClick={close}><X size={18} aria-hidden="true" /></button>
    </div>
    <p className="inspector-intro">What was saved from the source, and what the software checked.</p>
    {!research.answerLoaded ? <p role="status">Loading evidence…</p> : position && research.answer
      ? <EvidenceBody answer={research.answer} position={position} showClaim={showClaim} move={cite => {
        const claim = research.answer!.claims[position.claim]
        setParams({ evidence: claim.citations[cite].passage_id, finding: String(claim.ordinal) }); heading.current?.focus()
      }} />
      : <p role="alert" className="error-state">This passage isn't available in this investigation.</p>}
  </aside>
}
