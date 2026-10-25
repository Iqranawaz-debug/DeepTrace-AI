import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../app/App'
import { getHealth } from '../api/client'

beforeEach(() => vi.stubGlobal('fetch', vi.fn(async (url) => ({ ok: true, json: async () => String(url).includes('/api/investigations') ? { items: [], total: 0 } : { status: 'ok', version: '0.1.0' } }))))

describe('foundation', () => {
  it('renders honest empty state and no unbuilt controls', async () => {
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    expect(screen.getByRole('heading', { name: 'Investigations' })).toBeInTheDocument()
    expect(await screen.findByText('No investigations yet')).toBeInTheDocument()
    expect(screen.getByText('Mock / offline workspace')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /start research|resume|upload/i })).not.toBeInTheDocument()
    expect(await screen.findByText('Local backend connected')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({ credentials: 'omit' }))
  })

  it('navigates to settings and moves focus', async () => {
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    await userEvent.click(screen.getByRole('link', { name: 'Settings' }))
    expect(screen.getByRole('heading', { name: 'Settings', level: 1 })).toHaveFocus()
    expect(screen.getByText('Credentials cannot be entered in this version. Future live features will require explicit consent before sending data.')).toBeInTheDocument()
  })

  it('reports errors and retries safely', async () => {
    let failed = false
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url === '/api/health' && !failed) { failed = true; throw new Error('private detail') }
      return { ok: true, json: async () => String(url).includes('/api/investigations') ? { items: [], total: 0 } : { status: 'ok', version: '0.1.0' } } as Response
    })
    render(<RouterProvider router={createMemoryRouter([{ path: "*", element: <App /> }])} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Local backend unavailable')
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
    expect(await screen.findByText('Local backend connected')).toBeInTheDocument()
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
