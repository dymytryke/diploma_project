<template>
  <div class="p-4 sm:p-6">
    <h1 class="text-3xl font-semibold text-gray-800 mb-6">{{ $t('auditLogView.title') }}</h1>

    <!-- Filters -->
    <div class="mb-6 p-4 bg-white shadow rounded-lg">
      <h2 class="text-xl font-medium text-gray-700 mb-3">{{ $t('auditLogView.filtersTitle') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label for="filterProject" class="block text-sm font-medium text-gray-700">{{ $t('auditLogView.filterProjectIdLabel') }}</label>
          <input type="text" id="filterProject" v-model="filters.project_id" @keyup.enter="applyFiltersAndResetPage"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 :placeholder="$t('auditLogView.filterProjectPlaceholder')">
        </div>
        <div>
          <label for="filterUser" class="block text-sm font-medium text-gray-700">{{ $t('auditLogView.filterUserIdLabel') }}</label>
          <input type="text" id="filterUser" v-model="filters.user_id" @keyup.enter="applyFiltersAndResetPage"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 :placeholder="$t('auditLogView.filterUserPlaceholder')">
        </div>
        <div>
          <label for="filterAction" class="block text-sm font-medium text-gray-700">{{ $t('auditLogView.filterActionLabel') }}</label>
          <input type="text" id="filterAction" v-model="filters.action" @keyup.enter="applyFiltersAndResetPage"
                 class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 :placeholder="$t('auditLogView.filterActionPlaceholder')">
        </div>
      </div>
      <div class="mt-4 flex justify-end space-x-3">
        <button @click="clearFiltersAndResetPage"
                :disabled="isLoading"
                class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-200">
          {{ $t('common.clearFilters') }}
        </button>
        <button @click="applyFiltersAndResetPage"
                :disabled="isLoading"
                class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-blue-300">
          <span v-if="isLoading && applyingFilters">{{ $t('common.applying') }}</span>
          <span v-else-if="isLoading && !applyingFilters">{{ $t('common.loading') }}</span>
          <span v-else>{{ $t('auditLogView.applyFiltersButton') }}</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !auditEvents.length && !applyingFilters" class="text-center text-gray-500 py-10">
      <p>{{ $t('auditLogView.loadingEvents') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-red-500 p-4 bg-red-100 rounded-md shadow">
      <p>{{ $t('auditLogView.errorLoadingEvents') }}: {{ error.message || $t('common.unknownError') }}</p>
      <p v-if="error.response && error.response.data && error.response.data.detail">
        {{ $t('common.serverErrorPrefix') }}: {{ typeof error.response.data.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response.data.detail) }}
      </p>
    </div>

    <!-- Audit Events Table -->
    <div v-else-if="auditEvents.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderTimestamp') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderUserId') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderAction') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderObjectType') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderObjectId') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderProjectId') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('auditLogView.tableHeaderDetails') }}</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="event in auditEvents" :key="event.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ formatTimestamp(event.timestamp) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.user_id">{{ truncateId(event.user_id) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ event.action }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ event.object_type }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.object_id">{{ truncateId(event.object_id) }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 break-all" :title="event.project_id || $t('common.notAvailable')">{{ event.project_id ? truncateId(event.project_id) : $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 text-sm text-gray-700">
              <button @click="showDetails(event)" class="text-blue-500 hover:text-blue-700 underline">
                {{ $t('common.viewDetails') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <!-- Pagination Controls -->
      <div v-if="totalPages > 0" class="py-3 px-6 flex justify-between items-center border-t">
        <span class="text-sm text-gray-700">
          {{ $t('common.paginationSummary', { page: currentPage, totalPages: totalPages, total: totalEvents }) }}
        </span>
        <div class="space-x-1">
          <button @click="goToPage(currentPage - 1)" :disabled="!canGoPrevious || isLoading"
                  class="px-3 py-1 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ $t('common.previous') }}
          </button>
          <button @click="goToPage(currentPage + 1)" :disabled="!canGoNext || isLoading"
                  class="px-3 py-1 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ $t('common.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- No Events Found -->
    <div v-else-if="!isLoading" class="text-center text-gray-500 py-10">
      <p>{{ $t('auditLogView.noEventsFound') }}</p>
    </div>

    <!-- Details Modal -->
    <Teleport to="body">
      <div v-if="showDetailsModal" class="fixed inset-0 bg-gray-600 bg-opacity-75 z-50 flex items-center justify-center p-4 overflow-y-auto">
        <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h4 class="text-xl font-semibold">{{ $t('auditLogView.detailsModalTitle') }}</h4>
            <button @click="closeDetailsModal" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
          </div>
          <div class="overflow-y-auto">
            <pre class="text-sm bg-gray-100 p-3 rounded whitespace-pre-wrap break-all">{{ JSON.stringify(selectedEventDetails, null, 2) }}</pre>
          </div>
          <div class="mt-6 text-right">
            <button @click="closeDetailsModal" class="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400">
              {{ $t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const { t, d } = useI18n();

const auditEvents = ref([]);
const isLoading = ref(false);
const applyingFilters = ref(false);
const error = ref(null);

const filters = reactive({
  project_id: '', // Renamed to match API query param alias
  user_id: '',    // Renamed to match API query param alias
  action: ''
});

// Pagination state
const currentPage = ref(1);
const pageSize = ref(20); // Default page size, should match backend
const totalEvents = ref(0);
const totalPages = ref(0);

const showDetailsModal = ref(false);
const selectedEventDetails = ref(null);

const authStore = useAuthStore();
const router = useRouter();

const canGoPrevious = computed(() => currentPage.value > 1);
const canGoNext = computed(() => currentPage.value < totalPages.value);

async function fetchAuditEvents(isFilterAction = false) {
  isLoading.value = true;
  if (isFilterAction) {
    applyingFilters.value = true;
  }
  error.value = null;
  try {
    const queryParams = {
      page: currentPage.value,
      size: pageSize.value
    };
    if (filters.project_id) queryParams.project_id = filters.project_id;
    if (filters.user_id) queryParams.user_id = filters.user_id;
    if (filters.action) queryParams.action = filters.action;

    // Pass queryParams as { params: queryParams } for GET requests with axios
    const response = await apiService.get('/audit', { params: queryParams });
    
    auditEvents.value = response.data.items;
    totalEvents.value = response.data.total;
    totalPages.value = response.data.pages;
    currentPage.value = response.data.page; // API returns current page
    pageSize.value = response.data.size;   // API returns current size
    
  } catch (err) {
    console.error('Failed to fetch audit events:', err);
    error.value = err.response?.data || err;
    // Reset if error occurs, or handle more gracefully
    auditEvents.value = [];
    totalEvents.value = 0;
    totalPages.value = 0;
  } finally {
    isLoading.value = false;
    applyingFilters.value = false;
  }
}

function applyFiltersAndResetPage() {
  currentPage.value = 1; // Reset to first page when filters change
  fetchAuditEvents(true);
}

function clearFiltersAndResetPage() {
  filters.project_id = '';
  filters.user_id = '';
  filters.action = '';
  currentPage.value = 1; // Reset to first page
  fetchAuditEvents(true);
}

function goToPage(pageNumber) {
  if (pageNumber >= 1 && pageNumber <= totalPages.value && pageNumber !== currentPage.value) {
    currentPage.value = pageNumber;
    fetchAuditEvents();
  } else if (pageNumber < 1 && totalPages.value > 0) { // Handle edge case if trying to go before first page
    currentPage.value = 1;
    fetchAuditEvents();
  } else if (pageNumber > totalPages.value && totalPages.value > 0) { // Handle edge case if trying to go after last page
    currentPage.value = totalPages.value;
    fetchAuditEvents();
  }
}

function formatTimestamp(timestamp) {
  if (!timestamp) return t('common.notAvailable');
  try {
    // Example using vue-i18n's date formatting (ensure 'short' is defined in your i18n config)
    // return d(new Date(timestamp), 'short'); 
    return new Date(timestamp).toLocaleString(); // Fallback
  } catch (e) {
    return timestamp;
  }
}

function truncateId(id, length = 8) {
  if (!id) return t('common.notAvailable');
  if (id.length <= length) return id;
  return `${id.substring(0, length)}...`;
}

function showDetails(event) {
  selectedEventDetails.value = event.details;
  showDetailsModal.value = true;
}

function closeDetailsModal() {
  showDetailsModal.value = false;
  selectedEventDetails.value = null;
}

onMounted(() => {
  if (!authStore.isAdmin) {
    router.push({ name: 'home' });
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