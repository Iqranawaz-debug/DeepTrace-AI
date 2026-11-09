import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpenCheck, FileText, FolderSearch, Globe, Plus, Quote } from 'lucide-react'
import { getOverview, type Overview as OverviewData, type OverviewItem } from '../../api/client'
import { EmptyState } from '../../components/States'
import { eventText } from '../research/tracker'

const SCOPES: Record<string, string> = { research_pipeline: 'Research', plan_generation: 'Plan generation', evidence_collection: 'Collection' }

/** "3 minutes ago" style, from real timestamps only. */
function relative(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const format = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  const steps: [number, Intl.RelativeTimeFormatUnit][] = [[60, 'second'], [60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month']]
  let value = seconds
  for (const [size, unit] of steps) { if (Math.abs(value) < size) return format.format(Math.round(value), unit); value /= size }
  return format.format(Math.round(value), 'year')
}

function Stat({ icon: Icon, label, value, detail }: { icon: typeof Globe; label: string; value: string; detail?: string }) {
  return <li className="stat-card"><span className="stat-icon"><Icon size={18} aria-hidden="true" /></span><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong>{detail && <span className="stat-detail">{detail}</span>}</li>
}

function ContinueCard({ item }: { item: OverviewItem }) {
  const href = `/investigations/${encodeURIComponent(item.id)}`
  return <li className="continue-card">
    <div className="card-head"><span className="chip">{item.lifecycle ?? 'Draft'}</span><time className="stat-detail" dateTime={item.updated_at}>Updated {relative(item.updated_at)}</time></div>
    <h3><Link to={href} className="card-link">{item.title}</Link></h3>
    <p className="continue-question">{item.question}</p>
    <ul className="meta-row" aria-label={`Progress for ${item.title}`}>
      <li>{item.plan_steps} plan {item.plan_steps === 1 ? 'step' : 'steps'}</li>
      <li>{item.sources_read} of {item.sources} sources read</li>
      <li>{item.cited_findings} cited {item.cited_findings === 1 ? 'finding' : 'findings'}</li>
      <li>{item.report_version ? `Report v${item.report_version}` : 'No report yet'}</li>
    </ul>
  </li>
}

export function Overview() {
  const [state, setState] = useState<{ data?: OverviewData; error?: boolean }>({})
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    getOverview().then(data => { if (active) setState({ data }) }).catch(() => { if (active) setState({ error: true }) })
    return () => { active = false }
  }, [attempt])
  const { data } = state
  return <>
    <div className="page-head"><div><p className="eyebrow">Command Center</p><h1 tabIndex={-1}>Overview</h1><p className="page-sub">Everything below is counted from what is saved on this computer.</p></div>
      <Link to="/new" className="button primary"><Plus size={16} aria-hidden="true" />New investigation</Link></div>
    {state.error ? <div role="alert" className="error-state">Could not load the overview. Saved work is unchanged.<button className="button secondary" onClick={() => { setState({}); setAttempt(attempt + 1) }}>Retry overview</button></div>
      : !data ? <div aria-busy="true"><p role="status" className="sr-only">Loading overview…</p><ul className="stat-grid">{[0, 1, 2, 3, 4].map(n => <li key={n} className="stat-card skeleton-card" />)}</ul></div>
      : data.totals.investigations === 0 ? <EmptyState action={<Link to="/new" className="button primary">Create an investigation</Link>} />
      : <>
        <ul className="stat-grid" aria-label="Totals">
          <Stat icon={FolderSearch} label="Investigations" value={data.totals.investigations.toLocaleString()} />
          <Stat icon={Globe} label="Sources read" value={data.totals.sources_read.toLocaleString()} detail={`of ${data.totals.sources.toLocaleString()} considered`} />
          <Stat icon={Quote} label="Saved passages" value={data.totals.passages.toLocaleString()} />
          <Stat icon={BookOpenCheck} label="Cited findings" value={data.totals.cited_findings.toLocaleString()} detail="in latest answers" />
          <Stat icon={FileText} label="Reports" value={data.totals.reports.toLocaleString()} detail="generated and your own" />
        </ul>
        <div className="overview-grid">
          <section aria-labelledby="continue-title">
            <div className="section-head"><h2 id="continue-title">Continue investigating</h2><Link to="/investigations">View all</Link></div>
            {data.recent.length ? <ul className="continue-grid">{data.recent.map(item => <ContinueCard key={item.id} item={item} />)}</ul>
              : <p className="outline-muted">All investigations are archived. <Link to="/investigations">Open the library</Link>.</p>}
          </section>
          <section aria-labelledby="activity-title" className="activity-card">
            <div className="section-head"><h2 id="activity-title">Recent activity</h2></div>
            {data.activity.length ? <ol className="activity-feed">{data.activity.map((event, index) => <li key={`${event.created_at}-${index}`}>
              <span className="feed-dot" aria-hidden="true" />
              <div><p><strong>{eventText(event.event_type)}</strong>{event.scope && SCOPES[event.scope] ? <span className="outline-muted"> · {SCOPES[event.scope]}</span> : null}</p>
                <p className="outline-muted"><Link to={`/investigations/${encodeURIComponent(event.investigation_id)}`}>{event.title}</Link> · <time dateTime={event.created_at}>{relative(event.created_at)}</time></p></div>
            </li>)}</ol> : <p className="outline-muted">No runs yet. Activity from plan generation and research appears here.</p>}
          </section>
        </div>
      </>}
  </>
}
