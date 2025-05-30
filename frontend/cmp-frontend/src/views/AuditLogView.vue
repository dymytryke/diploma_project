<template>
  <div class="p-4 sm:p-6">
    <h1 class="text-3xl font-semibold text-gray-800 mb-6">Audit Log</h1>

    <!-- Filters -->
    <div class="mb-6 p-4 bg-white shadow rounded-lg">
      <h2 class="text-xl font-medium text-gray-700 mb-3">Filters</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label for="filterProject" class="block text-sm font-medium text-gray-700">Project ID</label>
          <input type="text" id="filterProject" v-model="filters.project" @keyup.enter="applyFilters"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 placeholder="Optional Project UUID">
        </div>
        <div>
          <label for="filterUser" class="block text-sm font-medium text-gray-700">User ID</label>
          <input type="text" id="filterUser" v-model="filters.user" @keyup.enter="applyFilters"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 placeholder="Optional User UUID">
        </div>
        <div>
          <label for="filterAction" class="block text-sm font-medium text-gray-700">Action</label>
          <input type="text" id="filterAction" v-model="filters.action" @keyup.enter="applyFilters"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 placeholder="e.g., create_project, update_ec2">
        </div>
      </div>
      <div class="mt-4 flex justify-end">
        <button @click="applyFilters"
                :disabled="isLoading"
                class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-blue-300">
          <span v-if="isLoading">Loading...</span>
          <span v-else>Apply Filters / Refresh</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !auditEvents.length" class="text-center text-gray-500 py-10">
      <p>Loading audit events...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-red-500 p-4 bg-red-100 rounded-md shadow">
      <p>Error loading audit events: {{ error.message || 'Unknown error' }}</p>
      <p v-if="error.response && error.response.data && error.response.data.detail">
        Server: {{ typeof error.response.data.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response.data.detail) }}
      </p>
    </div>

    <!-- Audit Events Table -->
    <div v-else-if="auditEvents.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Object Type</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Object ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="event in auditEvents" :key="event.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ formatTimestamp(event.timestamp) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.user_id">{{ truncateId(event.user_id) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ event.action }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ event.object_type }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.object_id">{{ truncateId(event.object_id) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.project_id || 'N/A'">{{ event.project_id ? truncateId(event.project_id) : 'N/A' }}</td>
            <td class="px-6 py-4 text-sm text-gray-700">
              <pre class="text-xs bg-gray-100 p-2 rounded overflow-x-auto max-w-xs">{{ JSON.stringify(event.details, null, 2) }}</pre>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- No Events Found -->
    <div v-else class="text-center text-gray-500 py-10">
      <p>No audit events found matching your criteria.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const auditEvents = ref([]);
const isLoading = ref(false);
const error = ref(null);

const filters = reactive({
  project: '',
  user: '',
  action: ''
});

const authStore = useAuthStore();
const router = useRouter();

async function fetchAuditEvents() {
  isLoading.value = true;
  error.value = null;
  try {
    const params = {};
    if (filters.project) params.project = filters.project;
    if (filters.user) params.user = filters.user;
    if (filters.action) params.action = filters.action;

    const response = await apiService.get('/audit', params ); // Pass params as the second argument for GET
    auditEvents.value = response.data;
  } catch (err) {
    console.error('Failed to fetch audit events:', err);
    error.value = err.response?.data || err;
  } finally {
    isLoading.value = false;
  }
}

function applyFilters() {
  fetchAuditEvents();
}

function formatTimestamp(timestamp) {
  if (!timestamp) return 'N/A';
  try {
    return new Date(timestamp).toLocaleString();
  } catch (e) {
    return timestamp; 
  }
}

function truncateId(id, length = 8) {
  if (!id) return 'N/A';
  if (id.length <= length) return id;
  return `${id.substring(0, length)}...`;
}

onMounted(() => {
  if (!authStore.isAdmin) {
    router.push({ name: 'home' }); // Redirect if not admin
    return;
  }
  fetchAuditEvents(); 
});
</script>

<style scoped>
pre {
  white-space: pre-wrap; 
  word-break: break-all;
}
</style>