<script setup>
import { ref, onMounted, computed } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n'; // Import useI18n

const authStore = useAuthStore();
const router = useRouter();
const { isLoggedIn, currentUser, isAdmin } = storeToRefs(authStore);
const isMobileMenuOpen = ref(false);

const { locale, t } = useI18n(); // Get locale and t function

const availableLocales = computed(() => {
  return ['en', 'uk']; 
});

onMounted(async () => {
  await authStore.initializeAuth();
  const savedLocale = localStorage.getItem('locale');
  if (savedLocale && availableLocales.value.includes(savedLocale)) {
    locale.value = savedLocale;
  } else {
    const browserLang = navigator.language.split('-')[0];
    if (availableLocales.value.includes(browserLang)) {
      locale.value = browserLang;
    }
    // If locale.value is still not set or not in availableLocales, it will use the default from i18n setup
    localStorage.setItem('locale', locale.value); // Persist the determined locale
  }
});

function handleLogout() {
  authStore.logout();
  isMobileMenuOpen.value = false;
  router.push({ name: 'login' }); // Use named route for login
}

function switchLocale(newLocale) {
  if (availableLocales.value.includes(newLocale)) {
    locale.value = newLocale;
    localStorage.setItem('locale', newLocale);
    isMobileMenuOpen.value = false; // Close mobile menu on language change
  }
}
</script>

<template>
  <div id="app-container" class="flex flex-col min-h-screen">
    <!-- Navigation Bar -->
    <header class="bg-gray-800 text-white shadow-md">
      <nav class="container mx-auto px-4 sm:px-6 py-3 flex flex-wrap justify-between items-center">
        <router-link to="/" class="text-xl font-bold hover:text-gray-300">
          {{ t('navigation.dashboard') }}
        </router-link>

        <div class="flex items-center"> <!-- Container for menu button and lang switcher -->
          <!-- Language Switcher - Desktop -->
          <div class="hidden sm:flex items-center mr-4">
            <select :value="locale" @change="switchLocale($event.target.value)" class="bg-gray-700 text-white py-1 px-2 rounded text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-gray-500 cursor-pointer">
              <option v-for="lang in availableLocales" :key="`desktop-${lang}`" :value="lang">{{ lang.toUpperCase() }}</option>
            </select>
          </div>

          <button @click="isMobileMenuOpen = !isMobileMenuOpen" class="sm:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white">
            <span class="sr-only">{{ t('app.openMainMenu') }}</span>
            <!-- Icon when menu is closed. -->
            <svg v-if="!isMobileMenuOpen" class="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
            </svg>
            <!-- Icon when menu is open. -->
            <svg v-else class="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Desktop Menu Links -->
        <div class="hidden sm:flex sm:items-center sm:space-x-4">
          <router-link v-if="isLoggedIn" to="/projects" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">{{ t('navigation.projects') }}</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/users" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">{{ t('navigation.users') }}</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/audit" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">{{ t('navigation.auditLog') }}</router-link>
        </div>
        
        <!-- User Info / Login / Logout for Desktop -->
        <div class="hidden sm:flex sm:items-center sm:ml-6">
          <div v-if="isLoggedIn" class="ml-auto flex items-center space-x-4">
            <span class="px-2 py-1 text-gray-300 text-sm">{{ t('common.welcome') }}, {{ currentUser?.email }} ({{ currentUser?.role_id ? t(`roles.${currentUser.role_id}`) : '' }})</span>
            <button @click="handleLogout" class="block w-full text-left sm:w-auto px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700">{{ t('navigation.logout') }}</button>
          </div>
          <div v-else class="ml-auto flex items-center space-x-4">
            <router-link to="/login" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">{{ t('navigation.login') }}</router-link>
            <router-link to="/signup" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">{{ t('navigation.signup') }}</router-link>
          </div>
        </div>
      </nav>

      <!-- Mobile Menu -->
      <div :class="{'block': isMobileMenuOpen, 'hidden': !isMobileMenuOpen}" class="sm:hidden border-t border-gray-700">
        <div class="px-2 pt-2 pb-3 space-y-1">
          <router-link v-if="isLoggedIn" to="/projects" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.projects') }}</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/users" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.users') }}</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/audit" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md textbase font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.auditLog') }}</router-link>
           <!-- Language Switcher - Mobile -->
          <div class="px-3 py-2">
            <select :value="locale" @change="switchLocale($event.target.value)" class="bg-gray-700 text-white py-1 px-2 rounded text-sm w-full appearance-none focus:outline-none focus:ring-1 focus:ring-gray-500 cursor-pointer">
              <option v-for="lang in availableLocales" :key="`mobile-${lang}`" :value="lang">{{ lang.toUpperCase() }}</option>
            </select>
          </div>
        </div>
        <div class="pt-4 pb-3 border-t border-gray-700">
          <div v-if="isLoggedIn" class="px-2 space-y-1">
            <p class="block px-3 py-2 rounded-md text-base font-medium text-gray-300">{{ t('common.welcome') }}, {{ currentUser?.email }} ({{ currentUser?.role_id ? t(`roles.${currentUser.role_id}`) : '' }})</p>
            <button @click="handleLogout" class="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.logout') }}</button>
          </div>
          <div v-else class="px-2 space-y-1">
            <router-link to="/login" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.login') }}</router-link>
            <router-link to="/signup" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md textbase font-medium text-gray-300 hover:bg-gray-700 hover:text-white">{{ t('navigation.signup') }}</router-link>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="flex-grow container mx-auto px-4 sm:px-6 py-8">
      <router-view />
    </main>

    <!-- Footer (Optional) -->
    <footer class="bg-gray-700 text-white text-center p-4">
      <p>&copy; {{ new Date().getFullYear() }} {{ t('navigation.dashboard') }}. {{ t('app.allRightsReserved') }}</p>
    </footer>
  </div>
</template>

<style>
/* Global styles can go here or in a separate CSS file imported in main.js */
#app-container {
  /* You can add global layout styles here if needed */
}
/* Basic styling for select dropdown arrow */
select {
  background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23CCCCCC%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E');
  background-repeat: no-repeat;
  background-position: right .7em top 50%;
  background-size: .65em auto;
  padding-right: 2.5em; /* Make space for the arrow */
}
</style>
