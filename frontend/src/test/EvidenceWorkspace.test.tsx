import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { EvidenceWorkspace } from '../features/evidence/EvidenceWorkspace'
import * as api from '../api/client'

vi.mock('../api/client', () => ({ getProviders: vi.fn(), listRuns: vi.fn(), listSources: vi.fn(), getPlan: vi.fn(), setCollectionConsent: vi.fn(), startCollection: vi.fn(), cancelCollection: vi.fn(), getSource: vi.fn(), getPassages: vi.fn(), listSavedUrls: vi.fn(), saveUrl: vi.fn(), ApiError: class extends Error { status = 0; detail = '' } }))
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getProviders).mockResolvedValue({ fixture_collection: true, consent: false, live_network: false })
  vi.mocked(api.listRuns).mockResolvedValue([])
  vi.mocked(api.listSources).mockResolvedValue([])
  vi.mocked(api.getPlan).mockResolvedValue({ id: null, revision_no: 0, items: [] })
  vi.mocked(api.listSavedUrls).mockResolvedValue([])
})
it('clearly labels synthetic data and requires explicit consent', async () => {
  render(<EvidenceWorkspace investigationId="test" />)
  expect(await screen.findByText('No collection runs yet.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Collect synthetic evidence' })).toBeDisabled()
  const enable = screen.getByRole('button', { name: 'Enable synthetic collection' })
  expect(enable).toBeDisabled()
  const user = userEvent.setup()
  await user.click(screen.getByRole('checkbox'))
  await user.click(enable)
  await waitFor(() => expect(api.setCollectionConsent).toHaveBeenCalledWith(true))
  expect(screen.getByText(/Live research is disabled/)).toBeVisible()
})
it('rejects real URLs without requesting a collection', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ fixture_collection: true, consent: true, live_network: false })
  render(<EvidenceWorkspace investigationId="test" />)
  const input = await screen.findByLabelText('Synthetic source URLs (one per line)')
  const user = userEvent.setup()
  await user.clear(input); await user.type(input, 'http://localhost/private')
  await user.click(screen.getByRole('button', { name: 'Collect synthetic evidence' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Real website collection is disabled')
  expect(api.startCollection).not.toHaveBeenCalled()
})
it('preserves a retry identifier when admission cannot be confirmed', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ fixture_collection: true, consent: true, live_network: false })
  vi.mocked(api.startCollection).mockRejectedValue(new Error('connection failed'))
  render(<EvidenceWorkspace investigationId="test" />)
  const button = await screen.findByRole('button', { name: 'Collect synthetic evidence' })
  const user = userEvent.setup()
  await user.click(button)
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be confirmed')
  await user.click(button)
  await waitFor(() => expect(api.startCollection).toHaveBeenCalledTimes(2))
  expect(vi.mocked(api.startCollection).mock.calls[0][1]).toBe(vi.mocked(api.startCollection).mock.calls[1][1])
})
it('offline mode exposes no collection action', async () => {
  vi.mocked(api.getProviders).mockResolvedValue({ fixture_collection: false, consent: false, live_network: false })
  render(<EvidenceWorkspace investigationId="test" />)
  expect(await screen.findByText(/Offline mode/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Collect synthetic evidence' })).not.toBeInTheDocument()
})
