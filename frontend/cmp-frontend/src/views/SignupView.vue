<template>
  <div class="p-4 max-w-md mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">Sign Up</h1>
    <form @submit.prevent="handleSignup" class="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
      <div v-if="signupError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ signupError }}
      </div>
      <div v-if="successMessage" class="mb-4 p-3 bg-green-100 text-green-700 rounded">
        {{ successMessage }}
      </div>
      <div class="mb-4">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="email">
          Email
        </label>
        <input v-model="email" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" id="email" type="email" placeholder="your@email.com" required>
      </div>
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="password">
          Password
        </label>
        <input v-model="password" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline" id="password" type="password" placeholder="******************" required>
      </div>
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="confirmPassword">
          Confirm Password
        </label>
        <input v-model="confirmPassword" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline" id="confirmPassword" type="password" placeholder="******************" required>
         <p v-if="passwordMismatch" class="text-red-500 text-xs italic">Passwords do not match.</p>
      </div>
      <div class="flex items-center justify-between">
        <button :disabled="isLoading || passwordMismatch" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full disabled:bg-green-300" type="submit">
          <span v-if="isLoading">Creating Account...</span>
          <span v-else>Sign Up</span>
        </button>
      </div>
      <div class="mt-4 text-center">
        <router-link to="/login" class="inline-block align-baseline font-bold text-sm text-blue-500 hover:text-blue-800">
          Already have an account? Login
        </router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const router = useRouter();

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);
const signupError = ref(''); // To display errors from the signup action
const successMessage = ref('');

const passwordMismatch = computed(() => {
  return password.value && confirmPassword.value && password.value !== confirmPassword.value;
});

async function handleSignup() {
  if (passwordMismatch.value) {
    signupError.value = 'Passwords do not match.';
    return;
  }
  if (!email.value || !password.value) {
    signupError.value = 'Email and password are required.';
    return;
  }

  isLoading.value = true;
  signupError.value = '';
  successMessage.value = '';

  const success = await authStore.signup({
    email: email.value,
    password: password.value,
  });

  if (success) {
    successMessage.value = 'Signup successful! Redirecting...';
    // The signup action in the store will handle redirection upon successful token storage
  } else {
    // Error message is set by the signup action in the store
    signupError.value = authStore.getSignupError || 'Signup failed. Please try again.';
  }

  isLoading.value = false;
}
</script>