import { useState } from 'react'
import { EvidenceWorkspace } from '../evidence/EvidenceWorkspace'
import { EvidenceReviewSection } from '../report/ReportPage'
import { useWorkspace } from './workspace'

export function EvidenceTab() {
  const { id } = useWorkspace()
  // A finished collection adds sources; the review then re-reads the saved passages.
  const [sources, setSources] = useState<number>()
  return <>
    <div className="panel-intro"><h2>Evidence</h2>
      <p>Saved passages are the only things findings and reports can cite. Record your own judgment on each one; classifications are yours, not verified facts.</p></div>
    <EvidenceReviewSection refresh={sources ?? 0} />
    <EvidenceWorkspace key={id} investigationId={id} onSources={setSources} />
  </>
}
