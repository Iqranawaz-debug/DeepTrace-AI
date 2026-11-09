import type { Budgets, GeneratedAnswer, Progress } from '../../api/client'

export type PhaseState = 'Completed' | 'In progress' | 'Pending' | 'Failed' | 'Cancelled' | 'Interrupted' | 'Budget reached' | 'Not reached'
export const PHASES = ['Plan', 'Discover', 'Read', 'Check', 'Report'] as const
const ACTIVE = ['queued', 'running']
const STOPPED: Record<string, PhaseState> = { failed: 'Failed', cancelled: 'Cancelled', interrupted: 'Interrupted', budget_reached: 'Budget reached' }

/** Phases genuinely finished. Partial reports never count: a stopped run stops at its real phase. */
function finished(progress: Progress): number {
  const done = new Set(progress.stages.filter(stage => stage.status === 'completed').map(stage => stage.stage_key))
  if (progress.status === 'completed') return PHASES.length
  if (!done.has('discover')) return 1
  if (!done.has('synthesize')) return 2
  if (!done.has('validate')) return 3
  return done.has('report') ? 5 : 4
}

/** DESIGN §9.2: a plan always precedes a research run, so Plan is already complete. */
export function phaseStates(progress: Progress): PhaseState[] {
  const count = finished(progress)
  const active = ACTIVE.includes(progress.status)
  return PHASES.map((_, index) => {
    if (index < count) return 'Completed'
    if (index === count) return active ? 'In progress' : STOPPED[progress.status] ?? 'Not reached'
    return active ? 'Pending' : 'Not reached'
  })
}

/** DESIGN §9.3: one line of real counts, shown only while a run is active. */
export function stageLine(progress: Progress, budgets: Budgets | null): string {
  if (progress.status === 'queued') return 'Waiting to start'
  if (progress.status !== 'running') return ''
  const done = new Set(progress.stages.map(stage => stage.stage_key))
  const count = finished(progress)
  if (count === 1) return `Searching for sources (${progress.usage.search_attempts}${budgets ? ` of ${budgets.max_searches}` : ''} searches)`
  if (count === 2) return done.has('rank') ? 'Drafting the answer' : `Reading sources (${progress.usage.pages_attempted}${budgets ? ` of ${budgets.max_pages}` : ''} pages)`
  return count === 3 ? 'Checking references and quotations' : 'Preparing the report'
}

const EVENTS: Record<string, string> = {
  queued: 'Run queued', running: 'Run started', source_saved: 'Source saved', source_failed: 'Source could not be read',
  discover_completed: 'Search finished', fetch_completed: 'Page fetching finished', rank_completed: 'Passages ranked', synthesize_completed: 'Answer drafted',
  validate_completed: 'Citations checked', report_completed: 'Report saved', plan_completed: 'Plan generated',
  completed: 'Run completed', failed: 'Run failed', cancelled: 'Run cancelled', interrupted: 'Run interrupted', budget_reached: 'Budget reached',
}
export const eventText = (code: string) => EVENTS[code] ?? 'Run updated'

/** DESIGN §10.5: an exact location or none at all; a highlight is never guessed. */
export function locateQuote(passage: string, quote: string | null): [number, number] | null {
  if (!quote?.trim()) return null
  const pattern = quote.trim().split(/\s+/).map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+')
  const found = new RegExp(pattern, 'u').exec(passage)
  return found ? [found.index, found.index + found[0].length] : null
}

export interface Position { claim: number; cite: number }

/** Where ?evidence= (and optionally ?finding=) points inside the latest generated answer. */
export function resolvePosition(answer: GeneratedAnswer | null, evidence: string | null, finding: string | null): Position | undefined {
  if (!evidence || !answer) return undefined
  const preferred = answer.claims.findIndex(claim => String(claim.ordinal) === finding)
  if (preferred >= 0) {
    const cite = answer.claims[preferred].citations.findIndex(citation => citation.passage_id === evidence)
    if (cite >= 0) return { claim: preferred, cite }
  }
  for (const [claim, item] of answer.claims.entries()) {
    const cite = item.citations.findIndex(citation => citation.passage_id === evidence)
    if (cite >= 0) return { claim, cite }
  }
  return undefined
}
