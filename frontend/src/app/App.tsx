import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tooltip from '@radix-ui/react-tooltip'
import { ChevronLeft, ChevronRight, Compass, FlaskConical, FolderSearch, LayoutDashboard, Menu, Plus, Radio, Settings as SettingsIcon, X } from 'lucide-react'
import { Dashboard } from '../features/investigations/Dashboard'
import { InvestigationForm, UnsavedChanges } from '../features/investigations/InvestigationForm'
import { Overview } from '../features/overview/Overview'
import { ReportTab } from '../features/report/ReportPage'
import { SourcesTab } from '../features/evidence/SourcesPage'
import { ProviderSetup } from '../features/settings/ProviderSetup'
import { Findings } from '../features/research/GeneratedResults'
import { EvidenceTab } from '../features/workspace/EvidenceTab'
import { InvestigationLayout } from '../features/workspace/InvestigationLayout'
import { PlanTab } from '../features/workspace/PlanTab'
import { getHealth, getMode } from '../api/client'
import { ErrorState, LoadingState } from '../components/States'

const SECTIONS = [
  ['Research', [['/', 'Overview', LayoutDashboard, true], ['/investigations', 'Investigations', FolderSearch, false]]],
  ['Preferences', [['/settings', 'Settings', SettingsIcon, false]]],
] as const

function Navigation({ close }: { close?: () => void }) {
  return <nav aria-label="Main">
    <Link to="/new" className="button primary nav-new" onClick={close} aria-label="New investigation"><Plus size={16} aria-hidden="true" /><span>New investigation</span></Link>
    {SECTIONS.map(([section, links]) => <div key={section} role="group" aria-labelledby={`nav-${section}`} className="nav-group">
      <p id={`nav-${section}`} className="nav-section">{section}</p>
      {links.map(([to, label, Icon, end]) => <Tooltip.Root key={to}><Tooltip.Trigger asChild><NavLink to={to} end={end} onClick={close} aria-label={label}>
        <Icon size={18} aria-hidden="true" /><span>{label}</span></NavLink></Tooltip.Trigger>
        <Tooltip.Portal><Tooltip.Content className="tooltip" side="right">{label}</Tooltip.Content></Tooltip.Portal></Tooltip.Root>)}
    </div>)}
  </nav>
}

function BackendStatus() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    getHealth(controller.signal).then(() => setState('ready')).catch(() => { if (!cancelled) setState('error') })
    return () => { cancelled = true; clearTimeout(timeout); controller.abort() }
  }, [attempt])
  if (state === 'loading') return <LoadingState />
  if (state === 'error') return <ErrorState retry={() => { setState('loading'); setAttempt(attempt + 1) }} />
  return <p className="connection" role="status"><span className="status-dot" />Local backend connected <span className="mono">/api/health</span></p>
}

function SettingsPage() {
  return <><div className="page-head"><div><p className="eyebrow">Preferences</p><h1 tabIndex={-1}>Settings</h1>
    <p className="page-sub">Providers, consent and what stays on this computer.</p></div></div>
    <ProviderSetup />
    <section className="card"><h2>Local storage</h2><p className="card-text">SQLite stores application data in your local user application-data directory, outside this repository.</p>
      <p className="card-text">Your investigations are stored on this computer. Searches, page requests and selected text still go to the providers you configure.</p>
      <p className="card-text">Investigations, plans, sources and reports are saved on this computer. Backups made during schema upgrades remain in the data folder. API keys are kept in Windows Credential Manager, never in the database.</p></section>
    <BackendStatus /></>
}

function SetupPage() {
  return <><div className="page-head"><div><p className="eyebrow">Setup</p><h1 tabIndex={-1}>Set up research</h1>
    <p className="page-sub">Mock mode works right away with no account. Live research needs your own free-tier keys and your explicit consent for each provider.</p></div></div>
    <ProviderSetup /><Link to="/">Return to Overview</Link></>
}

/** The research mode, always visible as a header chip. Its full meaning is in the tooltip and for screen readers. */
function ModeChip() {
  const [mode, setMode] = useState<string | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    getMode(controller.signal).then(setMode).catch(() => {})
    return () => controller.abort()
  }, [])
  const live = mode === 'live_free'
  const [label, detail] = live ? ['Live research (free tier)', 'Approved queries, passages and page requests leave this computer.'] : ['Mock / offline workspace', 'Live research and external providers are disabled.']
  return <Tooltip.Root><Tooltip.Trigger asChild><div className={`mode-chip ${live ? 'live' : ''}`} role="region" aria-label="Research mode" tabIndex={0}>
    {live ? <Radio size={14} aria-hidden="true" /> : <FlaskConical size={14} aria-hidden="true" />}<strong>{label}</strong><span className="sr-only"> {detail}</span></div></Tooltip.Trigger>
    <Tooltip.Portal><Tooltip.Content className="tooltip" side="bottom" align="end">{detail}</Tooltip.Content></Tooltip.Portal></Tooltip.Root>
}

function crumb(path: string): string {
  if (path === '/') return 'Overview'
  if (path === '/settings') return 'Settings'
  if (path === '/setup') return 'Setup'
  if (path === '/new') return 'New investigation'
  if (path === '/investigations') return 'Investigations'
  if (path.startsWith('/investigations/')) return 'Investigation'
  return 'Not found'
}

/** Keyed by id so switching tabs keeps the shared research state, but a different investigation starts fresh. */
function KeyedInvestigation() {
  const { id = '' } = useParams()
  return <InvestigationLayout key={id} />
}

export function App() { return <UnsavedChanges><Shell /></UnsavedChanges> }

const investigationOf = (path: string) => /^\/investigations\/[^/]+/.exec(path)?.[0] ?? null

function Shell() {
  const location = useLocation()
  const main = useRef<HTMLElement>(null)
  const previous = useRef<string | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('deeptrace.sidebar') === 'collapsed' } catch { return false }
  })
  const workspace = investigationOf(location.pathname)
  useEffect(() => {
    document.title = `${crumb(location.pathname)} — DeepTrace AI`
    // Switching tabs inside one investigation keeps focus on the tab the user chose.
    if (!workspace || workspace !== previous.current) main.current?.querySelector('h1')?.focus()
    previous.current = workspace
  }, [location.pathname, workspace])
  function toggleSidebar() {
    setCollapsed(!collapsed)
    try { localStorage.setItem('deeptrace.sidebar', !collapsed ? 'collapsed' : 'expanded') } catch { /* Optional UI preference. */ }
  }
  return <Tooltip.Provider delayDuration={400}><a className="skip-link" href="#main">Skip to main content</a>
    <div className={`shell ${collapsed ? 'collapsed' : ''}`}>
      <aside className="sidebar" aria-label="Application navigation"><Link to="/" className="brand" aria-label="DeepTrace AI home">
        <Compass size={26} aria-hidden="true" /><span>DeepTrace <small>AI</small></span></Link>
        <p className="tagline">Research you can trace.</p><Navigation />
        <div className="sidebar-bottom"><span className="local-note"><span className="status-dot" /> Local workspace</span>
          <Tooltip.Root><Tooltip.Trigger asChild><button className="collapse-button" onClick={toggleSidebar} aria-expanded={!collapsed} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? <ChevronRight aria-hidden="true" /> : <ChevronLeft aria-hidden="true" />}<span>Collapse sidebar</span></button></Tooltip.Trigger>
            <Tooltip.Portal><Tooltip.Content className="tooltip">{collapsed ? 'Expand sidebar' : 'Collapse sidebar'}</Tooltip.Content></Tooltip.Portal></Tooltip.Root></div>
      </aside>
      <div className="workspace"><header className="header"><div className="header-context">
        <Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}><Dialog.Trigger asChild><button className="icon-button mobile-menu" aria-label="Open navigation"><Menu aria-hidden="true" /></button></Dialog.Trigger>
          <Dialog.Portal><Dialog.Overlay className="scrim" /><Dialog.Content className="mobile-nav"><Dialog.Title>DeepTrace AI</Dialog.Title>
            <Dialog.Description>Research you can trace.</Dialog.Description><Dialog.Close className="icon-button close" aria-label="Close navigation"><X aria-hidden="true" /></Dialog.Close>
            <Navigation close={() => setMobileOpen(false)} /></Dialog.Content></Dialog.Portal></Dialog.Root>
        <span>Workspace</span><span className="header-slash">/</span><strong>{crumb(location.pathname)}</strong></div>
        <div className="header-end"><ModeChip /><span className="version mono">v0.1.0</span></div></header>
        <main id="main" ref={main} className={workspace ? 'wide' : undefined}><Routes>
          <Route path="/" element={<><Overview /><BackendStatus /></>} />
          <Route path="/investigations" element={<><Dashboard /><BackendStatus /></>} />
          <Route path="/new" element={<><div className="page-head"><div><p className="eyebrow">Research</p><h1 tabIndex={-1}>New investigation</h1><p className="page-sub">Create a local draft. Nothing is sent anywhere until you generate a plan or start research.</p></div></div><InvestigationForm /><BackendStatus /></>} />
          <Route path="/investigations/:id" element={<KeyedInvestigation />}>
            <Route index element={<PlanTab />} />
            <Route path="findings" element={<Findings />} />
            <Route path="sources" element={<SourcesTab />} />
            <Route path="evidence" element={<EvidenceTab />} />
            <Route path="report" element={<ReportTab />} />
          </Route>
          <Route path="/setup" element={<SetupPage />} /><Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<><h1 tabIndex={-1}>This page doesn’t exist</h1><Link to="/">Return to Overview</Link></>} /></Routes></main>
      </div>
    </div></Tooltip.Provider>
}
