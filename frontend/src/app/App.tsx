import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tooltip from '@radix-ui/react-tooltip'
import { ArrowRight, ChevronLeft, ChevronRight, Compass, Database, FlaskConical,
  LayoutDashboard, Menu, Settings as SettingsIcon, ShieldCheck, X } from 'lucide-react'
import { getHealth } from '../api/client'
import { EmptyState, ErrorState, LoadingState } from '../components/States'

function Navigation({ close }: { close?: () => void }) {
  return <nav aria-label="Main"><Tooltip.Root><Tooltip.Trigger asChild><NavLink to="/" end onClick={close} aria-label="Dashboard">
    <LayoutDashboard size={20} aria-hidden="true" /><span>Dashboard</span></NavLink></Tooltip.Trigger>
    <Tooltip.Portal><Tooltip.Content className="tooltip" side="right">Dashboard</Tooltip.Content></Tooltip.Portal></Tooltip.Root>
    <Tooltip.Root><Tooltip.Trigger asChild><NavLink to="/settings" onClick={close} aria-label="Settings">
      <SettingsIcon size={20} aria-hidden="true" /><span>Settings</span></NavLink></Tooltip.Trigger>
      <Tooltip.Portal><Tooltip.Content className="tooltip" side="right">Settings</Tooltip.Content></Tooltip.Portal></Tooltip.Root></nav>
}

function BackendStatus() {
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    getHealth(controller.signal).then(() => setState('ready')).catch(() => {
      if (!cancelled) setState('error')
    })
    let cancelled = false
    return () => { cancelled = true; clearTimeout(timeout); controller.abort() }
  }, [attempt])
  if (state === 'loading') return <LoadingState />
  if (state === 'error') return <ErrorState retry={() => { setState('loading'); setAttempt(attempt + 1) }} />
  return <p className="connection" role="status"><span className="status-dot" />Local backend connected <span className="mono">/api/health</span></p>
}

function Dashboard() {
  return <><div className="page-intro"><p className="eyebrow">Your research workspace</p>
    <h1 tabIndex={-1}>Investigations</h1><p>Follow the question. Keep the evidence in view.</p></div>
    <div className="list-header"><h2>Investigation library</h2><span className="label">Phase 1 · Foundation</span></div>
    <EmptyState action={<Link className="button primary" to="/settings">Explore the foundation <ArrowRight size={16} aria-hidden="true" /></Link>} />
    <div className="principles"><article><Database aria-hidden="true" /><h3>Stored on this computer</h3><p>SQLite provides local storage for future investigations.</p></article>
      <article><ShieldCheck aria-hidden="true" /><h3>External providers disabled</h3><p>No questions or source content leave this application.</p></article>
      <article><Compass aria-hidden="true" /><h3>Built for traceable research</h3><p>Sources, passages and cited reports are planned for later phases.</p></article></div>
    <BackendStatus /></>
}

function SettingsPage() {
  return <><div className="page-intro"><p className="eyebrow">Local application</p><h1 tabIndex={-1}>Settings</h1>
    <p>A clear view of what this foundation can do.</p></div>
    <section className="settings-card"><h2>Provider boundaries</h2><p>Mock / offline foundation. Research execution is not available.</p>
      <dl><div><dt>Gemini · language model</dt><dd>Disabled</dd></div><div><dt>Tavily · web search</dt><dd>Disabled</dd></div>
        <div><dt>Paid API usage</dt><dd>Disabled</dd></div><div><dt>Telemetry</dt><dd>Not collected</dd></div></dl>
      <p>Credentials cannot be entered in this version. Future live features will require explicit consent before sending data.</p></section>
    <section className="settings-card"><h2>Local storage</h2><p>SQLite stores application data in your local user application-data directory, outside this repository.</p>
      <p>No research records are created by this foundation. Backups made during future schema upgrades remain on this computer.</p></section>
    <BackendStatus /></>
}

export function App() {
  const location = useLocation()
  const main = useRef<HTMLElement>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('deeptrace.sidebar') === 'collapsed' } catch { return false }
  })
  useEffect(() => {
    document.title = `${location.pathname === '/settings' ? 'Settings' : 'Investigations'} — DeepTrace AI`
    main.current?.querySelector('h1')?.focus()
  }, [location.pathname])
  function toggleSidebar() {
    setCollapsed(!collapsed)
    try { localStorage.setItem('deeptrace.sidebar', !collapsed ? 'collapsed' : 'expanded') } catch { /* Optional UI preference. */ }
  }
  return <Tooltip.Provider delayDuration={400}><a className="skip-link" href="#main">Skip to main content</a>
    <div className={`shell ${collapsed ? 'collapsed' : ''}`}>
      <aside className="sidebar" aria-label="Application navigation"><Link to="/" className="brand" aria-label="DeepTrace AI home">
        <Compass size={28} aria-hidden="true" /><span>DeepTrace <small>AI</small></span></Link>
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
        <span>Workspace</span><span className="header-slash">/</span><strong>{location.pathname === '/settings' ? 'Settings' : 'Dashboard'}</strong></div>
        <span className="version mono">v0.1.0</span></header>
        <div className="mode-banner"><FlaskConical size={16} aria-hidden="true" /><strong>Mock / offline foundation</strong><span>Research and external providers are disabled.</span></div>
        <main id="main" ref={main}><Routes><Route path="/" element={<Dashboard />} /><Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<><h1 tabIndex={-1}>This page doesn’t exist</h1><Link to="/">Return to Dashboard</Link></>} /></Routes></main>
      </div>
    </div></Tooltip.Provider>
}
