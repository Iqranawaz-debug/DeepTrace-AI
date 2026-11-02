import { Link } from 'react-router-dom'

const LINKS = [['workspace', 'Workspace', ''], ['sources', 'Sources', '/sources'], ['report', 'Report', '/report']] as const

export function InvestigationNav({ id, current }: { id: string; current: typeof LINKS[number][0] }) {
  const base = `/investigations/${encodeURIComponent(id)}`
  return <nav aria-label="Investigation" className="actions">{LINKS.map(([key, label, suffix]) => <Link key={key} to={base + suffix} aria-current={current === key ? 'page' : undefined}>{label}</Link>)}</nav>
}
