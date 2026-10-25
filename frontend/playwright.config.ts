import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

export default defineConfig({
  testDir: './e2e', workers: 1, reporter: 'list',
  use: { ...devices['Desktop Chrome'], channel: 'msedge', baseURL: 'http://127.0.0.1:5173' },
  webServer: [
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: false },
    { command: `"${path.resolve('../backend/.venv/Scripts/python.exe')}" -m deeptrace serve`, url: 'http://127.0.0.1:8000/api/ready',
      env: { DEEPTRACE_DATA_DIR: path.resolve('.cache/browser-data') }, reuseExistingServer: false },
  ],
})
