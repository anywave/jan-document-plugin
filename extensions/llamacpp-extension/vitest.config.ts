import { defineConfig } from 'vitest/config'
import settingJson from './settings.json' with { type: 'json' }
import pkgJson from './package.json' with { type: 'json' }

export default defineConfig({
  define: {
    SETTINGS: JSON.stringify(settingJson),
    ENGINE: JSON.stringify(pkgJson.engine),
    IS_WINDOWS: JSON.stringify(process.platform === 'win32'),
    IS_MAC: JSON.stringify(process.platform === 'darwin'),
    IS_LINUX: JSON.stringify(process.platform === 'linux'),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
