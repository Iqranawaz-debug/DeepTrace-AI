import { AlertCircle, Search } from 'lucide-react'
import type { ReactNode } from 'react'

export function EmptyState({ action }: { action: ReactNode }) {
  return <section className="empty-state" aria-labelledby="empty-title">
    <div className="empty-icon"><Search size={48} strokeWidth={1.5} aria-hidden="true" /></div>
    <p className="eyebrow">A place for your questions</p>
    <h2 id="empty-title">No investigations yet</h2>
    <p>Your research begins with a question.<br />Create a local draft and build your manual research plan.</p>
    {action}
  </section>
}

export function LoadingState() {
  return <div aria-busy="true" aria-label="Checking local backend" className="loading-state">
    <span className="skeleton" aria-hidden="true" /> Checking local backend…
  </div>
}

export function ErrorState({ retry }: { retry: () => void }) {
  return <div className="error-state" role="alert">
    <AlertCircle size={18} aria-hidden="true" />
    <div><strong>Local backend unavailable</strong><p>The connection failed. Existing data has not been deleted. Start the backend and retry.</p></div>
    <button className="button secondary" onClick={retry}>Retry connection</button>
  </div>
}
