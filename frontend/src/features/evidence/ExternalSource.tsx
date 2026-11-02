import { ExternalLink } from 'lucide-react'

/** DESIGN §10.7: visible, labeled, never automatic. Only http(s) ever becomes a link. */
export function ExternalSource({ url }: { url: string }) {
  let parsed: URL
  try { parsed = new URL(url) } catch { return <p className="mono hash">{url}</p> }
  if (!['http:', 'https:'].includes(parsed.protocol)) return <p className="mono hash">{url}</p>
  return <p className="external-source"><a href={parsed.href} target="_blank" rel="noopener noreferrer">Open original <ExternalLink size={14} aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span></a> <span className="mono hash">{parsed.hostname}</span></p>
}
