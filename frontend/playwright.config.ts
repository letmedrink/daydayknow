import { defineConfig } from '@playwright/test';

const backendPython = process.env.BACKEND_PYTHON || '../backend/.venv/bin/python';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH } : undefined,
  },
  webServer: [
    {
      command: `cd ../backend && DATA_DIR=./data-e2e ${backendPython} -m uvicorn app.main:app --host 127.0.0.1 --port 8011`,
      url: 'http://127.0.0.1:8011/health', reuseExistingServer: true,
    },
    {
      command: 'VITE_API_URL=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5174',
      url: 'http://127.0.0.1:5174', reuseExistingServer: true,
    },
  ],
});
