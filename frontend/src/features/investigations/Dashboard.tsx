import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listInvestigations, type InvestigationList } from '../../api/client'
import { EmptyState } from '../../components/States'

export function Dashboard() {
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<{ data?: InvestigationList; error?: string }>({})
  useEffect(() => {
    let current = true
    listInvestigations(query, offset).then(data => { if (current) setState({ data }) }).catch(() => { if (current) setState({ error: 'Could not load investigations. Retry when the local backend is available.' }) })
    return () => { current = false }
  }, [query, offset, attempt])
  function reload() { setState({}); setAttempt(attempt + 1) }
  return <><div className="page-intro"><p className="eyebrow">Your local research workspace</p><h1 tabIndex={-1}>Investigations</h1><p>Shape your questions. Save a manual plan. Research execution remains disabled.</p></div>
    <div className="list-header"><h2>Investigation library</h2><Link to="/new" className="button primary">New investigation</Link></div>
    <label className="field">Search investigations<input type="search" maxLength={1000} value={query} onChange={event => { setQuery(event.target.value); setOffset(0); setState({}) }} /></label>
    <p className="label">Most recently updated first · Search title and question on this computer</p>
    {!state.data && !state.error && <p role="status">Loading investigations…</p>}
    {state.error && <div role="alert" className="error-state">{state.error}<button className="button secondary" onClick={reload}>Retry library</button></div>}
    {state.data && <>{state.data.items.length === 0 ? query ? <p role="status">No matching investigations.</p> : <EmptyState action={<Link to="/new" className="button primary">Create an investigation</Link>} /> :
      <ul className="investigation-list">{state.data.items.map(item => <li key={item.id} className="settings-card"><div className="list-header"><h2><Link to={`/investigations/${item.id}`}>{item.title}</Link></h2><span className="label">Draft</span></div><p className="research-question">{item.question}</p><div className="record-dates"><span>Created <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></span><span>Updated <time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleString()}</time></span></div><Link to={`/investigations/${item.id}`}>Continue editing<span className="sr-only"> {item.title}</span></Link></li>)}</ul>}
      <div className="actions"><button className="button secondary" disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - 25)); setState({}) }}>Previous page</button><span>{state.data.total} investigations</span><button className="button secondary" disabled={offset + 25 >= state.data.total} onClick={() => { setOffset(offset + 25); setState({}) }}>Next page</button></div></>}
  </>
}
