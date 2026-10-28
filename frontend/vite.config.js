import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiUrl = (env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
  const url = new URL(apiUrl)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('VITE_API_URL debe ser una URL HTTP o HTTPS sin credenciales ni parámetros')
  }
  if (process.env.RENDER && (!env.VITE_API_URL || url.protocol !== 'https:')) {
    throw new Error('Configura VITE_API_URL con la dirección HTTPS pública del backend en Render')
  }
  return {
    plugins: [react(), {
      name: 'version-publicada',
      generateBundle() {
        this.emitFile({
          type: 'asset',
          fileName: 'deploy-version.json',
          source: JSON.stringify({ commit: process.env.RENDER_GIT_COMMIT || process.env.GITHUB_SHA || 'local' }),
        })
      },
    }],
    define: { __API_URL__: JSON.stringify(apiUrl) },
  }
})
