<template>
  <div class="p-4 max-w-md mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">{{ $t('signup.title') }}</h1>
    <form @submit.prevent="handleSignup" class="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
      <div v-if="signupError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ signupError }} <!-- This error comes from the store or local validation, needs to be translated if local -->
      </div>
      <div v-if="successMessage" class="mb-4 p-3 bg-green-100 text-green-700 rounded">
        {{ successMessage }} <!-- This message is local, needs to be translated -->
      </div>
      <div class="mb-4">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="email">
          {{ $t('common.email') }}
        </label>
        <input v-model="email" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" id="email" type="email" :placeholder="$t('signup.emailPlaceholder')" required>
      </div>
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="password">
          {{ $t('signup.passwordLabel') }}
        </label>
        <input v-model="password" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline" id="password" type="password" :placeholder="$t('signup.passwordPlaceholder')" required>
      </div>
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-bold mb-2" for="confirmPassword">
          {{ $t('signup.confirmPasswordLabel') }}
        </label>
        <input v-model="confirmPassword" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline" id="confirmPassword" type="password" :placeholder="$t('signup.passwordPlaceholder')" required>
         <p v-if="passwordMismatch" class="text-red-500 text-xs italic">{{ $t('signup.passwordsDoNotMatch') }}</p>
      </div>
      <div class="flex items-center justify-between">
        <button :disabled="isLoading || passwordMismatch" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full disabled:bg-green-300" type="submit">
          <span v-if="isLoading">{{ $t('signup.creatingAccount') }}</span>
          <span v-else>{{ $t('signup.signUpButton') }}</span>
        </button>
      </div>
      <div class="mt-4 text-center">
        <router-link to="/login" class="inline-block align-baseline font-bold text-sm text-blue-500 hover:text-blue-800">
          {{ $t('signup.loginLink') }}
        </router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from 'vue-i18n'; // Import useI18n

const { t } = useI18n(); // Initialize t function
const authStore = useAuthStore();
const router = useRouter();

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);
const signupError = ref('');
const successMessage = ref('');

const passwordMismatch = computed(() => {
  return password.value && confirmPassword.value && password.value !== confirmPassword.value;
});

async function handleSignup() {
  if (passwordMismatch.value) {
    signupError.value = t('signup.passwordsDoNotMatch'); // Use t()
    return;
  }
  if (!email.value || !password.value) {
    signupError.value = t('signup.emailAndPasswordRequired'); // Use t()
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
    successMessage.value = t('signup.signupSuccessRedirecting'); // Use t()
    // The signup action in the store will handle redirection upon successful token storage
  } else {
    // Error message is set by the signup action in the store
    // If authStore.getSignupError is already a translated string or a key, this is fine.
    // If it's a raw error message from the backend, it won't be translated here.
    signupError.value = authStore.getSignupError || t('signup.signupFailed'); // Use t() for fallback
  }

  isLoading.value = false;
}
</script>