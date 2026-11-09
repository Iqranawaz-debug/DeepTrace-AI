import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../app/App'
import { getHealth } from '../api/client'

const EMPTY_OVERVIEW = { totals: { investigations: 0, sources: 0, sources_read: 0, passages: 0, cited_findings: 0, reports: 0 }, recent: [], activity: [] }
const reply = (url: unknown) => String(url).includes('/api/overview') ? EMPTY_OVERVIEW : String(url).includes('/api/investigations') ? { items: [], total: 0 } : { status: 'ok', version: '0.1.0' }
beforeEach(() => vi.stubGlobal('fetch', vi.fn(async (url) => ({ ok: true, json: async () => reply(url) }))))

describe('foundation', () => {
  it('renders honest empty state and no unbuilt controls', async () => {
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    expect(screen.getByRole('heading', { name: 'Overview', level: 1 })).toBeInTheDocument()
    expect(await screen.findByText('No investigations yet')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Research' })).toHaveTextContent('OverviewInvestigations')
    expect(screen.getByRole('group', { name: 'Preferences' })).toHaveTextContent('Settings')
    expect(screen.getByRole('region', { name: 'Research mode' })).toHaveTextContent('Live research and external providers are disabled.')
    expect(screen.getByText('Mock / offline workspace')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start research|resume|upload/i })).not.toBeInTheDocument()
    expect(await screen.findByText('Local backend connected')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({ credentials: 'omit' }))
  })

  it('navigates to settings and moves focus', async () => {
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    await userEvent.click(screen.getByRole('link', { name: 'Settings' }))
    expect(screen.getByRole('heading', { name: 'Settings', level: 1 })).toHaveFocus()
    expect(screen.getByText('Providers, consent and what stays on this computer.')).toBeInTheDocument()
  })

  it('reports errors and retries safely', async () => {
    let failed = false
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url === '/api/health' && !failed) { failed = true; throw new Error('private detail') }
      return { ok: true, json: async () => reply(url) } as Response
    })
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Local backend unavailable')
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
    expect(await screen.findByText('Local backend connected')).toBeInTheDocument()
  })

  it('shows real totals, continue cards and activity on the overview', async () => {
    const overview = { totals: { investigations: 2, sources: 10, sources_read: 7, passages: 31, cited_findings: 5, reports: 3 },
      recent: [{ id: 'a', title: 'Admissions study', question: 'How is AI used in admissions?', lifecycle: 'Completed', updated_at: new Date().toISOString(), sources: 10, sources_read: 7, plan_steps: 5, report_version: 2, cited_findings: 5 }],
      activity: [{ event_type: 'completed', created_at: new Date().toISOString(), investigation_id: 'a', title: 'Admissions study', scope: 'research_pipeline' }] }
    vi.mocked(fetch).mockImplementation(async (url) => ({ ok: true, json: async () => String(url).includes('/api/overview') ? overview : reply(url) }) as Response)
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    const totals = await screen.findByRole('list', { name: 'Totals' })
    expect(totals).toHaveTextContent('Sources read7of 10 considered')
    expect(totals).toHaveTextContent('Cited findings5')
    for (const link of screen.getAllByRole('link', { name: 'Admissions study' })) expect(link).toHaveAttribute('href', '/investigations/a')
    expect(screen.getByRole('list', { name: 'Progress for Admissions study' })).toHaveTextContent('5 plan steps7 of 10 sources read5 cited findingsReport v2')
    expect(screen.getByText('Run completed')).toBeInTheDocument()
    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
  })

  it('persists collapsed navigation preference', async () => {
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    await userEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }))
    expect(localStorage.getItem('deeptrace.sidebar')).toBe('collapsed')
  })

  it('rejects malformed API payloads', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({ status: 'pretend' }) } as Response)
    await expect(getHealth()).rejects.toThrow('Unexpected health response')
  })
})
