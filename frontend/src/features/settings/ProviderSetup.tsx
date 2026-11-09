import { useCallback, useEffect, useState } from 'react'
import { ApiError, getProviders, grantConsent, removeCredential, revokeConsent, saveCredential, type ProviderInfo, type Providers } from '../../api/client'

const message = (failure: unknown) => failure instanceof ApiError ? [failure.message, failure.detail].filter(Boolean).join(' ') : 'The local request failed. Nothing was changed.'

function ProviderCard({ provider, onChange }: { provider: ProviderInfo; onChange: () => Promise<void> }) {
  const [key, setKey] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  async function act(work: () => Promise<unknown>, done: string) {
    setBusy(true); setError(''); setStatus('')
    try { await work(); setKey(''); setConfirmed(false); await onChange(); setStatus(done) }
    catch (failure) { setError(message(failure)) } finally { setBusy(false) }
  }
  return <li className="settings-card"><h3>{provider.role} · {provider.id === 'public_web' ? 'public websites' : provider.id}</h3>
    <dl><div><dt>Data sent</dt><dd>{provider.data_sent}</dd></div><div><dt>Key</dt><dd>{provider.credential_state}</dd></div><div><dt>Consent</dt><dd>{provider.consent ? 'Accepted' : 'Not accepted'} · {provider.disclosure_version}</dd></div></dl>
    <p>{provider.notice}</p>
    {provider.needs_credential && <form onSubmit={event => { event.preventDefault(); void act(() => saveCredential(provider.id, key), 'Key saved. It will not be shown again.') }}>
      {/* Write-only: the stored key is never loaded back into this field. */}
      <label className="field">{provider.role} API key<input type="password" autoComplete="off" spellCheck={false} minLength={8} maxLength={512} value={key} onChange={event => setKey(event.target.value)} /><span>Saved to Windows Credential Manager; never to the database or logs</span></label>
      <div className="actions"><button className="button secondary" disabled={busy || key.length < 8}>Save key</button>{provider.credential_state !== 'Not configured' && <button type="button" className="button secondary" disabled={busy} onClick={() => void act(() => removeCredential(provider.id), 'Key removed.')}>Remove key</button>}</div></form>}
    {provider.consent ? <button className="button secondary" disabled={busy} onClick={() => void act(() => revokeConsent(provider.id), 'Consent revoked. New requests are blocked; data already sent cannot be recalled.')}>Revoke consent</button> : <>
      <label className="check-row"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I reviewed this disclosure{provider.needs_credential ? ' and confirmed my account is on a free tier' : ''}.</label>
      <button className="button secondary" disabled={busy || !confirmed} onClick={() => void act(() => grantConsent(provider.id, provider.disclosure_version), 'Consent recorded.')}>Accept disclosure</button></>}
    {status && <p role="status">{status}</p>}{error && <p role="alert" className="error-state">{error}</p>}
  </li>
}

/** Shared by Settings and the setup page. Mode changes only through local configuration. */
export function ProviderSetup() {
  const [providers, setProviders] = useState<Providers>()
  const [failed, setFailed] = useState(false)
  const load = useCallback(async () => { setProviders(await getProviders()); setFailed(false) }, [])
  useEffect(() => {
    let active = true
    getProviders().then(value => { if (active) setProviders(value) }).catch(() => { if (active) setFailed(true) })
    return () => { active = false }
  }, [])
  if (failed) return <div role="alert" className="error-state">Could not read provider status. Saved keys and consent are unchanged.<button className="button secondary" onClick={() => void load().catch(() => setFailed(true))}>Retry providers</button></div>
  if (!providers) return <p role="status">Loading providers…</p>
  return <>
    <section className="settings-card"><h2>Research mode</h2>
      <p><strong>{providers.mode === 'live_free' ? 'Live (free tier)' : providers.mode === 'offline' ? 'Offline' : 'Mock / offline workspace'}</strong>. {providers.mode === 'mock' ? 'Simulated providers and synthetic fixtures. No key or account is needed and nothing leaves this computer.' : providers.mode === 'offline' ? 'Saved research can be read. New research is disabled.' : 'Approved requests go to the providers below.'}</p>
      {providers.mode !== 'live_free' && <><h3>To use live research</h3><ol className="setup-steps"><li>Add your keys and accept each disclosure below.</li><li>In <code>backend/.env</code>, set <code>DEEPTRACE_MODE=live_free</code> and <code>DEEPTRACE_LLM_MODEL</code> to a Gemini model you have confirmed is free for your account and region.</li><li>Restart the backend. A web page can never switch this on by itself.</li></ol></>}
      {(providers.blockers ?? []).length > 0 && providers.mode === 'live_free' && <><h3>Still needed</h3><ul>{providers.blockers?.map(item => <li key={item}>{item}</li>)}</ul></>}
      <dl><div><dt>Paid API usage</dt><dd>Disabled; no paid fallback exists</dd></div><div><dt>Telemetry</dt><dd>DeepTrace doesn't collect telemetry.</dd></div>{providers.llm_model && <div><dt>Model</dt><dd className="mono">{providers.llm_model}</dd></div>}</dl>
    </section>
    <ul className="provider-list">{(providers.providers ?? []).map(provider => <ProviderCard key={provider.id} provider={provider} onChange={load} />)}</ul>
  </>
}
