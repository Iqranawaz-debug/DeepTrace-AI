import { useEffect, useState } from 'react'
import { Ban, Circle, CircleCheck, CircleX, Gauge, Loader, Unplug } from 'lucide-react'
import { getRunEvents, type Progress, type RunEvent } from '../../api/client'
import { eventText, PHASES, phaseStates, stageLine, type PhaseState } from './tracker'

const ICONS: Record<PhaseState, typeof Circle> = { Completed: CircleCheck, 'In progress': Loader, Pending: Circle, Failed: CircleX, Cancelled: Ban, Interrupted: Unplug, 'Budget reached': Gauge, 'Not reached': Circle }

export function ResearchTracker({ progress }: { progress: Progress }) {
  const states = phaseStates(progress)
  const line = stageLine(progress, progress.budgets)
  return <>
    <ol className="phase-tracker" aria-label="Research progress">{PHASES.map((phase, index) => {
      const Icon = ICONS[states[index]]
      return <li key={phase} className={`phase phase-${states[index].toLowerCase().replaceAll(' ', '-')}`} aria-current={states[index] === 'In progress' ? 'step' : undefined}><Icon size={18} aria-hidden="true" /><strong>{phase}</strong><span>{states[index]}</span></li>
    })}</ol>
    {line && <p className="stage-line">{line}</p>}
  </>
}

/** Reverse-chronological log: fixed event text plus the queries this run actually sent. */
export function ActivityLog({ runId, investigationId, progress }: { runId: string; investigationId: string; progress: Progress }) {
  const [open, setOpen] = useState(false)
  const [events, setEvents] = useState<RunEvent[]>([])
  const [failed, setFailed] = useState(false)
  const count = progress.stages.length + progress.usage.pages_attempted + progress.usage.search_attempts
  useEffect(() => {
    if (!open) return
    let active = true
    getRunEvents(runId, investigationId).then(rows => { if (active) { setEvents(rows); setFailed(false) } }).catch(() => { if (active) setFailed(true) })
    return () => { active = false }
  }, [open, runId, investigationId, count, progress.status])
  const rows = [
    ...events.map(event => ({ at: event.created_at, key: event.id, text: eventText(event.event_type) })),
    ...progress.queries.map((query, index) => ({ at: query.searched_at ?? '', key: `query-${index}`, text: `Searched: ${query.query_text} (${query.status === 'completed' ? `${query.results_count ?? 0} results` : query.status.replaceAll('_', ' ')})` })),
  ].sort((a, b) => b.at.localeCompare(a.at))
  return <details className="activity-log" onToggle={event => setOpen(event.currentTarget.open)}><summary>Activity</summary>
    {failed ? <p role="alert" className="error-state">Could not load activity. The run is unaffected.</p> : !rows.length ? <p>No activity yet.</p> : <ol>{rows.map(row => <li key={row.key}><time className="mono" dateTime={row.at}>{row.at ? new Date(row.at).toLocaleTimeString() : ''}</time> {row.text}</li>)}</ol>}
  </details>
}
