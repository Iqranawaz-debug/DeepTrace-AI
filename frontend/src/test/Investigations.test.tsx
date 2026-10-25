import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { InvestigationForm, UnsavedChanges } from '../features/investigations/InvestigationForm'
import { Dashboard } from '../features/investigations/Dashboard'
import { ApiError } from '../api/client'
import * as api from '../api/client'

vi.mock('../api/client', async importOriginal => ({ ...await importOriginal<typeof api>(), createInvestigation: vi.fn(), editInvestigation: vi.fn(), listInvestigations: vi.fn() }))
const investigation: api.Investigation = { id: 'test-id', title: 'Local study', question: 'What should we investigate?', description: '', status: 'draft', created_at: '2026-10-25T00:00:00Z', updated_at: '2026-10-25T00:00:00Z' }
function show(element: React.ReactNode) {
  const router = createMemoryRouter([{ path: '*', element: <UnsavedChanges>{element}</UnsavedChanges> }])
  render(<RouterProvider router={router} />)
  return router
}
beforeEach(() => vi.clearAllMocks())

it('creates persisted work with a stable request id and navigates only after success', async () => {
  vi.mocked(api.createInvestigation).mockRejectedValueOnce(new ApiError(0)).mockResolvedValue(investigation)
  const router = show(<InvestigationForm />)
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/^Title/), 'Local study')
  await user.type(screen.getByLabelText(/^Main research question/), investigation.question)
  await user.click(screen.getByRole('button', { name: 'Create investigation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Your edits are still here')
  expect(router.state.location.pathname).toBe('/')
  expect(screen.getByLabelText(/^Title/)).toHaveValue('Local study')
  await user.click(screen.getByRole('button', { name: 'Create investigation' }))
  await waitFor(() => expect(router.state.location.pathname).toBe('/investigations/test-id'))
  expect(vi.mocked(api.createInvestigation).mock.calls[0][0]).toBe(vi.mocked(api.createInvestigation).mock.calls[1][0])
})

it('uses accessible constraints, keeps edits on conflict and blocks navigation', async () => {
  vi.mocked(api.editInvestigation).mockRejectedValue(new ApiError(409))
  const router = show(<InvestigationForm initial={investigation} />)
  const user = userEvent.setup()
  expect(screen.getByLabelText(/^Main research question/)).toHaveAttribute('minlength', '10')
  expect(screen.getByLabelText(/^Title/)).toBeRequired()
  await user.type(screen.getByLabelText(/^Title/), ' edited')
  await user.click(screen.getByRole('button', { name: 'Save details' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Newer changes exist')
  expect(screen.getByLabelText(/^Title/)).toHaveValue('Local study edited')
  await router.navigate('/settings')
  expect(await screen.findByRole('dialog')).toHaveTextContent('Leave unsaved changes?')
  await user.click(screen.getByRole('button', { name: 'Keep editing' }))
  expect(router.state.location.pathname).toBe('/')
})

it('lists saved investigations with local search and safe error recovery', async () => {
  vi.mocked(api.listInvestigations).mockRejectedValueOnce(new ApiError(0)).mockResolvedValue({ items: [investigation], total: 1 })
  show(<Dashboard />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load')
  await userEvent.click(screen.getByRole('button', { name: 'Retry library' }))
  expect(await screen.findByRole('link', { name: 'Local study' })).toHaveAttribute('href', '/investigations/test-id')
  await userEvent.type(screen.getByRole('searchbox'), 'local')
  await waitFor(() => expect(api.listInvestigations).toHaveBeenLastCalledWith('local', 0))
})

it('prevents leaving while a save is still in flight', async () => {
  let finish!: (value: api.Investigation) => void
  vi.mocked(api.editInvestigation).mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const router = show(<InvestigationForm initial={investigation} />)
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/^Title/), ' changed')
  await user.click(screen.getByRole('button', { name: 'Save details' }))
  await router.navigate('/settings')
  expect(await screen.findByRole('dialog')).toHaveTextContent('A save is in progress')
  expect(screen.getByRole('button', { name: 'Discard and leave' })).toBeDisabled()
  finish({ ...investigation, title: 'Local study changed', updated_at: '2026-10-25T01:00:00Z' })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Discard and leave' })).toBeEnabled())
})
