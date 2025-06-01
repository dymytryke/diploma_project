import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'

import App from './App.vue'
import router from './router'

// Import locale messages
import enMessages from './locales/en.json'
import ukMessages from './locales/uk.json'

const i18n = createI18n({
  legacy: false, 
  locale: localStorage.getItem('locale') || navigator.language.split('-')[0] || 'en', 
  fallbackLocale: 'en',
  messages: {
    en: enMessages,
    uk: ukMessages
  }
});

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n) // Use i18n

app.mount('#app')
