<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth'; // Import the auth store
import { storeToRefs } from 'pinia'; // Helper to make store state reactive

const authStore = useAuthStore();
const router = useRouter();
const { isLoggedIn, currentUser, isAdmin } = storeToRefs(authStore); // Make isAdmin reactive
const isMobileMenuOpen = ref(false);

// Call initializeAuth when the component is mounted
onMounted(async () => {
  await authStore.initializeAuth();
});

function handleLogout() {
  authStore.logout(); // Call the logout action from the store
  isMobileMenuOpen.value = false; // Close mobile menu on logout
  router.push('/login');
}
</script>

<template>
  <div id="app-container" class="flex flex-col min-h-screen">
    <!-- Navigation Bar -->
    <header class="bg-gray-800 text-white shadow-md">
      <nav class="container mx-auto px-4 sm:px-6 py-3 flex flex-wrap justify-between items-center">
        <router-link to="/" class="text-xl font-bold hover:text-gray-300">
          CMP Dashboard
        </router-link>

        <button @click="isMobileMenuOpen = !isMobileMenuOpen" class="sm:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white">
          <span class="sr-only">Open main menu</span>
          <!-- Icon when menu is closed. -->
          <svg v-if="!isMobileMenuOpen" class="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
          </svg>
          <!-- Icon when menu is open. -->
          <svg v-else class="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- Desktop Menu Links -->
        <div class="hidden sm:flex sm:items-center sm:space-x-4">
          <router-link v-if="isLoggedIn" to="/projects" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Projects</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/users" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Users</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/audit" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Audit Log</router-link>
        </div>
        
        <!-- User Info / Login / Logout for Desktop -->
        <div class="hidden sm:flex sm:items-center sm:ml-6">
          <div v-if="isLoggedIn" class="ml-auto flex items-center space-x-4">
            <span class="px-2 py-1 text-gray-300 text-sm">Welcome, {{ currentUser?.email }} ({{ currentUser?.role_id }})</span>
            <button @click="handleLogout" class="block w-full text-left sm:w-auto px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700">Logout</button>
          </div>
          <div v-else class="ml-auto flex items-center space-x-4">
            <router-link to="/login" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Login</router-link>
            <router-link to="/signup" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Sign Up</router-link>
          </div>
        </div>
      </nav>

      <!-- Mobile Menu -->
      <div :class="{'block': isMobileMenuOpen, 'hidden': !isMobileMenuOpen}" class="sm:hidden border-t border-gray-700">
        <div class="px-2 pt-2 pb-3 space-y-1">
          <router-link v-if="isLoggedIn" to="/projects" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Projects</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/users" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Users</router-link>
          <router-link v-if="isLoggedIn && isAdmin" to="/audit" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Audit Log</router-link>
        </div>
        <div class="pt-4 pb-3 border-t border-gray-700">
          <div v-if="isLoggedIn" class="px-2 space-y-1">
            <p class="block px-3 py-2 rounded-md text-base font-medium text-gray-300">Welcome, {{ currentUser?.email }} ({{ currentUser?.role_id }})</p>
            <button @click="handleLogout" class="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Logout</button>
          </div>
          <div v-else class="px-2 space-y-1">
            <router-link to="/login" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md textbase font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Login</router-link>
            <router-link to="/signup" @click="isMobileMenuOpen = false" class="block px-3 py-2 rounded-md textbase font-medium text-gray-300 hover:bg-gray-700 hover:text-white">Sign Up</router-link>
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
      <p>&copy; {{ new Date().getFullYear() }} CMP Dashboard. All rights reserved.</p>
    </footer>
  </div>
</template>

<style>
/* Global styles can go here or in a separate CSS file imported in main.js */
#app-container {
  /* You can add global layout styles here if needed */
}
</style>
