import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { PlanEditor } from '../features/plans/PlanEditor'
import { UnsavedChanges } from '../features/investigations/InvestigationForm'
import * as api from '../api/client'

vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<typeof api>(), savePlan: vi.fn() }))

it('adds, keyboard reorders, removes and saves stable step identifiers', async () => {
  const user = userEvent.setup()
  vi.mocked(api.savePlan).mockImplementation(async (_id, items, revision) => ({ id: 'plan', items, revision_no: revision + 1 }))
  render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <UnsavedChanges><PlanEditor investigationId="investigation" initial={{ id: null, items: [], revision_no: 0 }} onSaved={() => {}} /></UnsavedChanges> }])} />)
  await user.click(screen.getByRole('button', { name: 'Add step' }))
  await user.type(screen.getByLabelText(/^Sub-question 1/), 'First question')
  await user.click(screen.getByRole('button', { name: 'Add step' }))
  await user.type(screen.getByLabelText(/^Sub-question 2/), 'Second question')
  screen.getByRole('button', { name: 'Move up step 2' }).focus()
  await user.keyboard('{Enter}')
  expect(screen.getByLabelText(/^Sub-question 1/)).toHaveValue('Second question')
  expect(screen.getByText('Moved to position 1 of 2')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Save plan' }))
  expect(await screen.findByText('Plan saved locally · revision 1')).toBeInTheDocument()
  const savedIds = vi.mocked(api.savePlan).mock.calls[0][1].map(item => item.id)
  await user.click(screen.getByRole('button', { name: 'Remove step 2' }))
  await user.click(screen.getByRole('button', { name: 'Save plan' }))
  await waitFor(() => expect(api.savePlan).toHaveBeenLastCalledWith('investigation', [expect.objectContaining({ id: savedIds[0] })], 1))
  expect(await screen.findByText('Plan saved locally · revision 2')).toBeInTheDocument()
})

it('keeps unsaved plan edits after a failed save', async () => {
  vi.mocked(api.savePlan).mockRejectedValue(new api.ApiError(409))
  render(<RouterProvider router={createMemoryRouter([{ path: '*', element: <UnsavedChanges><PlanEditor investigationId="investigation" initial={{ id: 'plan', items: [{ id: 'step', sub_question: 'Saved question', search_query: null }], revision_no: 1 }} onSaved={() => {}} /></UnsavedChanges> }])} />)
  await userEvent.type(screen.getByLabelText(/^Sub-question 1/), ' edited')
  await userEvent.click(screen.getByRole('button', { name: 'Save plan' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Newer changes exist')
  expect(screen.getByLabelText(/^Sub-question 1/)).toHaveValue('Saved question edited')
  expect(screen.getByText('Unsaved plan')).toBeInTheDocument()
})
