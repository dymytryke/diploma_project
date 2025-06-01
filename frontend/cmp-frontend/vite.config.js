import { fileURLToPath, URL } from 'node:url'
import path from 'node:path' // Import path

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
import vueI18n from '@intlify/unplugin-vue-i18n/vite' // Import vueI18n

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
    vueI18n({ // Add and configure the vueI18n plugin
      include: path.resolve(__dirname, './src/locales/**'),
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    minify: false,
    // ...
  }
})
