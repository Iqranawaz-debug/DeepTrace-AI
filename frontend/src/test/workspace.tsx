import { render } from '@testing-library/react'
import { createMemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { UnsavedChanges } from '../features/investigations/InvestigationForm'
import { SourcesTab } from '../features/evidence/SourcesPage'
import { ReportTab } from '../features/report/ReportPage'
import { Findings } from '../features/research/GeneratedResults'
import { EvidenceTab } from '../features/workspace/EvidenceTab'
import { InvestigationLayout } from '../features/workspace/InvestigationLayout'
import { PlanTab } from '../features/workspace/PlanTab'

/** The real three-panel investigation workspace, routed exactly as the app routes it. */
export function renderWorkspace(path = '/investigations/inv') {
  const tree = <UnsavedChanges><Routes><Route path="/investigations/:id" element={<InvestigationLayout />}>
    <Route index element={<PlanTab />} /><Route path="findings" element={<Findings />} /><Route path="sources" element={<SourcesTab />} />
    <Route path="evidence" element={<EvidenceTab />} /><Route path="report" element={<ReportTab />} />
  </Route></Routes></UnsavedChanges>
  return render(<RouterProvider router={createMemoryRouter([{ path: '*', element: tree }], { initialEntries: [path] })} />)
}
