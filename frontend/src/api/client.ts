export interface Health { status: 'ok' | 'ready'; version: string }

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch('/api/health', { signal, credentials: 'omit', cache: 'no-store' })
  if (!response.ok) throw new Error('Local backend unavailable')
  const data: unknown = await response.json()
  if (!data || typeof data !== 'object' || !('status' in data) || data.status !== 'ok'
    || !('version' in data) || typeof data.version !== 'string') {
    throw new Error('Unexpected health response')
  }
  return { status: 'ok', version: data.version }
}
