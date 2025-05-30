<template>
  <div class="p-4 max-w-md mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">Login</h1>
    <form @submit.prevent="handleLogin" class="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
      <!-- Display API Login Error -->
      <div v-if="authStore.getLoginError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ authStore.getLoginError }}
      </div>
      <!-- Display local error message (can be removed if API error is sufficient) -->
      <div v-if="errorMessage && !authStore.getLoginError" class="mb-4 p-3 bg-yellow-100 text-yellow-700 rounded">
        {{ errorMessage }}
      </div>
      <div class="mb-4">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="username">
          Username
        </label>
        <input v-model="username" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" id="username" type="text" placeholder="Username" required>
      </div>
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="password">
          Password
        </label>
        <input v-model="password" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline" id="password" type="password" placeholder="******************" required>
      </div>
      <div class="flex items-center justify-between">
        <button :disabled="isLoading" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full disabled:bg-blue-300" type="submit">
          <span v-if="isLoading">Signing In...</span>
          <span v-else>Sign In</span>
        </button>
      </div>
      <!-- Add link to Signup page -->
      <div class="mt-4 text-center">
        <router-link to="/signup" class="inline-block align-baseline font-bold text-sm text-green-500 hover:text-green-800">
          Don't have an account? Sign Up
        </router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const username = ref('');
const password = ref('');
const isLoading = ref(false);
const errorMessage = ref(''); // For local validation/unexpected errors, less used now

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMessage.value = 'Username and password are required.'; // Basic local validation
    return;
  }
  isLoading.value = true;
  errorMessage.value = ''; // Clear local error
  // authStore.loginError is cleared within the action itself

  await authStore.login({ username: username.value, password: password.value });
  // Redirection or error display is handled by the store and template reactivity

  isLoading.value = false;
}
</script>