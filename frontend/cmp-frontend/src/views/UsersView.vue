<template>
  <div class="p-4 sm:p-6">
    <h1 class="text-2xl font-semibold text-gray-800 mb-6">{{ $t('usersView.title') }}</h1>

    <!-- Loading State -->
    <div v-if="isLoadingUsers" class="text-center text-gray-500 mt-10">
      <p>{{ $t('usersView.loadingUsers') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="usersError" class="text-center text-red-500 mt-10 p-4 bg-red-100 rounded">
      <p>{{ $t('usersView.errorLoadingUsers') }}: {{ usersError.message || $t('common.unknownError') }}</p>
      <p v-if="usersError.response && usersError.response.data && usersError.response.data.detail">
        {{ $t('common.serverErrorPrefix') }}: {{ typeof usersError.response.data.detail === 'string' ? usersError.response.data.detail : JSON.stringify(usersError.response.data.detail) }}
      </p>
    </div>

    <!-- Users Table -->
    <div v-else-if="users.length > 0" class="bg-white shadow-md rounded-lg overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.email') }}</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.role') }}</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('usersView.userId') }}</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('usersView.createdAt') }}</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="user in users" :key="user.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ user.email }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ $t(`roles.${user.role_id}`) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ user.id }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ new Date(user.created_at).toLocaleString() }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                @click="openEditUserRoleModal(user)"
                :disabled="user.id === authStore.currentUser?.id && user.role_id === 'admin'"
                class="text-yellow-600 hover:text-yellow-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                :title="$t('usersView.editRoleTitle')"
              >
                {{ $t('usersView.editRoleButton') }}
              </button>
              <button
                @click="openDeleteUserModal(user)"
                :disabled="user.id === authStore.currentUser?.id"
                class="text-red-600 hover:text-red-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                :title="$t('usersView.deleteUserTitle')"
              >
                {{ $t('common.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-center text-gray-500 mt-10">
      <p>{{ $t('usersView.noUsersFound') }}</p>
    </div>

    <!-- Edit User Role Modal -->
    <Teleport to="body">
      <div v-if="showEditRoleModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">{{ $t('usersView.editUserRoleModalTitle') }}</h3>
            <form @submit.prevent="submitEditUserRole" class="mt-2 px-7 py-3">
              <div v-if="modalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ modalError.message || $t('common.couldNotProcessRequest') }}</p>
                <p v-if="modalError.response && modalError.response.data && modalError.response.data.detail">
                  {{ $t('common.serverErrorPrefix') }}: {{ typeof modalError.response.data.detail === 'string' ? modalError.response.data.detail : JSON.stringify(modalError.response.data.detail) }}
                </p>
              </div>
              <div class="mb-4 text-left">
                <p class="text-sm text-gray-600">{{ $t('usersView.userLabel') }}: <strong class="text-gray-800">{{ userToEdit?.email }}</strong></p>
              </div>
              <div class="mb-4">
                <label for="userRole" class="block text-sm font-medium text-gray-700 text-left">{{ $t('common.role') }}</label>
                <select
                  id="userRole"
                  v-model="userToEdit.role_id"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="viewer">{{ $t('roles.viewer') }}</option>
                  <option value="devops">{{ $t('roles.devops') }}</option>
                  <option value="admin">{{ $t('roles.admin') }}</option>
                </select>
              </div>
              <div class="items-center px-4 py-3 space-x-4 flex justify-end">
                <button type="button" @click="closeEditUserRoleModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
                <button type="submit" :disabled="isProcessing" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                  <span v-if="isProcessing">{{ $t('common.saving') }}</span>
                  <span v-else>{{ $t('usersView.saveRoleButton') }}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete User Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteUserConfirmModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">{{ $t('usersView.deleteUserModalTitle') }}</h3>
            <div class="mt-2 px-7 py-3">
              <p class="text-sm text-gray-600">
                {{ $t('usersView.deleteUserConfirmation', { email: userToDelete?.email }) }}
              </p>
              <div v-if="modalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ modalError.message || $t('common.couldNotProcessRequest') }}</p>
                 <p v-if="modalError.response && modalError.response.data && modalError.response.data.detail">
                  {{ $t('common.serverErrorPrefix') }}: {{ typeof modalError.response.data.detail === 'string' ? modalError.response.data.detail : JSON.stringify(modalError.response.data.detail) }}
                </p>
              </div>
            </div>
            <div class="items-center px-4 py-3 space-x-4 flex justify-end">
              <button type="button" @click="closeDeleteUserModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
              <button @click="submitDeleteUser" :disabled="isProcessing" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
                <span v-if="isProcessing">{{ $t('common.deleting') }}</span>
                <span v-else>{{ $t('usersView.deleteUserButton') }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'; // Import computed
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from 'vue-i18n'; // Import useI18n

const { t } = useI18n(); // Initialize t function

const authStore = useAuthStore();

const users = ref([]);
const isLoadingUsers = ref(false);
const usersError = ref(null);

const showEditRoleModal = ref(false);
const userToEdit = ref(null);

const showDeleteUserConfirmModal = ref(false);
const userToDelete = ref(null);

const modalError = ref(null);
const isProcessing = ref(false);

// const globalRoles = ['viewer', 'devops', 'admin']; // Not directly used in template, roles are hardcoded in select

async function fetchUsers() {
  isLoadingUsers.value = true;
  usersError.value = null;
  try {
    const response = await apiService.get('/users');
    users.value = response.data;
  } catch (err) {
    console.error('Failed to fetch users:', err);
    usersError.value = err.response?.data || err;
  } finally {
    isLoadingUsers.value = false;
  }
}

onMounted(fetchUsers);

// --- Edit User Role Functions ---
function openEditUserRoleModal(user) {
  userToEdit.value = { ...user }; // Clone to avoid direct mutation
  modalError.value = null;
  showEditRoleModal.value = true;
}

function closeEditUserRoleModal() {
  showEditRoleModal.value = false;
  userToEdit.value = null;
}

async function submitEditUserRole() {
  if (!userToEdit.value || !userToEdit.value.role_id) {
    modalError.value = { message: t('usersView.roleIsRequiredError') }; // Localized error
    return;
  }
  isProcessing.value = true;
  modalError.value = null;
  try {
    const payload = { role_id: userToEdit.value.role_id };
    await apiService.patch(`/users/${userToEdit.value.id}/role`, payload);
    await fetchUsers(); // Refresh the user list
    closeEditUserRoleModal();
  } catch (err) {
    console.error('Failed to update user role:', err);
    modalError.value = err.response?.data || err;
  } finally {
    isProcessing.value = false;
  }
}

// --- Delete User Functions ---
function openDeleteUserModal(user) {
  userToDelete.value = { ...user }; // Clone
  modalError.value = null;
  showDeleteUserConfirmModal.value = true;
}

function closeDeleteUserModal() {
  showDeleteUserConfirmModal.value = false;
  userToDelete.value = null;
}

async function submitDeleteUser() {
  if (!userToDelete.value) return;
  isProcessing.value = true;
  modalError.value = null;
  try {
    await apiService.delete(`/users/${userToDelete.value.id}`);
    await fetchUsers(); // Refresh the user list
    closeDeleteUserModal();
  } catch (err) {
    console.error('Failed to delete user:', err);
    modalError.value = err.response?.data || err;
  } finally {
    isProcessing.value = false;
  }
}
</script>

<style scoped>
/* Scoped styles for UsersView */
</style>