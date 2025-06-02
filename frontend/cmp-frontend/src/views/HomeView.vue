<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n'; // Import useI18n

const { t } = useI18n(); // Initialize t function
const router = useRouter();
const authStore = useAuthStore();
const { currentUser, isLoggedIn, isAdmin } = storeToRefs(authStore);

// --- Projects Data ---
const recentProjects = ref([]);
const MAX_RECENT_PROJECTS = 3;

// --- Quick Stats ---
const quickStats = ref({
  totalProjects: 0,
  activeEc2Instances: 0,
  activeAzureVms: 0,
  totalUsers: null,
});
const isLoadingQuickStats = ref(false);
const quickStatsError = ref(null); // This will store the error message string (potentially from backend)

const welcomeMessage = computed(() => {
  if (isLoggedIn.value && currentUser.value) {
    return t('homeView.welcomeBack', { email: currentUser.value.email });
  }
  return t('homeView.welcomeGuest');
});

async function fetchDashboardData() {
  isLoadingQuickStats.value = true;
  quickStatsError.value = null;
  recentProjects.value = [];

  let allProjects = [];

  try {
    const projectsResponse = await apiService.get('/projects');
    allProjects = projectsResponse.data;
    quickStats.value.totalProjects = allProjects.length;

    const sortedProjects = [...allProjects].sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
    });
    recentProjects.value = sortedProjects.slice(0, MAX_RECENT_PROJECTS);

    let ec2Count = 0;
    let azureVmCount = 0;

    const resourcePromises = allProjects.map(async (project) => {
      try {
        const ec2Promise = apiService.get(`/resources/aws/ec2/${project.id}`);
        const azureVmPromise = apiService.get(`/resources/azure/vm/${project.id}`);
        const [ec2Response, azureResponse] = await Promise.all([ec2Promise, azureVmPromise]);
        ec2Response.data.forEach(ec2 => {
          if (ec2.status === 'running') ec2Count++;
        });
        azureResponse.data.forEach(vm => {
          if (vm.status === 'running') azureVmCount++;
        });
      } catch (projectResourceError) {
        console.warn(`Failed to fetch resources for project ${project.id}:`, projectResourceError);
      }
    });

    await Promise.all(resourcePromises);
    quickStats.value.activeEc2Instances = ec2Count;
    quickStats.value.activeAzureVms = azureVmCount;

    if (isAdmin.value) {
      try {
        const usersResponse = await apiService.get('/users');
        quickStats.value.totalUsers = usersResponse.data.length;
      } catch (userError) {
        console.error('Failed to fetch total users:', userError);
        quickStats.value.totalUsers = t('common.error'); // Use translated error string
      }
    }

  } catch (err) {
    console.error('Failed to fetch dashboard data:', err);
    quickStatsError.value = err.response?.data?.detail || err.message || t('homeView.errorLoadingDashboard'); // Use translated fallback
    quickStats.value.totalProjects = 0;
    quickStats.value.activeEc2Instances = 0;
    quickStats.value.activeAzureVms = 0;
    if (isAdmin.value) quickStats.value.totalUsers = t('common.error');
  } finally {
    isLoadingQuickStats.value = false;
  }
}

function navigateToProject(projectId) {
  router.push({ name: 'project-detail', params: { projectId } });
}

function navigateToProjects() {
  router.push('/projects');
}

onMounted(async () => {
  if (isLoggedIn.value) {
    await fetchDashboardData();
  }
});
</script>

<template>
  <div class="p-4 sm:p-6 space-y-8">
    <!-- 1. Welcome & Quick Stats -->
    <section>
      <h1 class="text-3xl font-bold text-gray-800 mb-2">{{ welcomeMessage }}</h1>
      <p v-if="isLoggedIn" class="text-gray-600">{{ $t('homeView.overviewLoggedIn') }}</p>
      <p v-else class="text-gray-600">{{ $t('homeView.overviewLoggedOut') }}</p>

      <!-- Quick Stats Display -->
      <div v-if="isLoggedIn" class="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">{{ $t('homeView.stats.totalProjects') }}</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.totalProjects }}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">{{ $t('homeView.stats.activeEc2') }}</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.activeEc2Instances }}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">{{ $t('homeView.stats.activeAzureVms') }}</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.activeAzureVms }}</p>
        </div>
        <div v-if="isAdmin" class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">{{ $t('homeView.stats.totalUsers') }}</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">
            {{ isLoadingQuickStats && quickStats.totalUsers === null ? '...' : (quickStats.totalUsers !== null ? quickStats.totalUsers : $t('common.notAvailable')) }}
          </p>
        </div>
      </div>
      <div v-if="isLoadingQuickStats && !quickStatsError" class="mt-4 text-sm text-gray-500">
        {{ $t('homeView.loadingStats') }}
      </div>
      <div v-if="quickStatsError" class="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
        <p>{{ $t('homeView.errorLoadingStatsPrefix') }}: {{ quickStatsError }}</p>
      </div>
    </section>

    <div v-if="isLoggedIn" class="space-y-8">
      <!-- 2. My Projects / Recent Projects -->
      <section>
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-semibold text-gray-700">{{ $t('homeView.recentProjectsTitle') }}</h2>
          <button @click="navigateToProjects" class="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            {{ $t('homeView.viewAllProjectsLink') }} &rarr;
          </button>
        </div>
        <div v-if="isLoadingQuickStats && recentProjects.length === 0" class="text-center py-6">
          <p class="text-gray-500">{{ $t('projectsView.loadingProjects') }}</p> <!-- Reusing from projectsView -->
        </div>
        <div v-else-if="!isLoadingQuickStats && quickStatsError && recentProjects.length === 0" class="p-4 bg-red-50 text-red-700 rounded-md">
          <p>{{ $t('homeView.errorLoadingRecentProjects') }}</p>
        </div>
        <div v-else-if="recentProjects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="project in recentProjects" :key="project.id"
               class="bg-white rounded-lg shadow-lg overflow-hidden transform hover:scale-105 transition-transform duration-200 cursor-pointer"
               @click="navigateToProject(project.id)">
            <div class="p-5">
              <h3 class="text-lg font-semibold text-gray-800 mb-2 truncate" :title="project.name">{{ project.name }}</h3>
              <p class="text-xs text-gray-500 mb-1">{{ $t('projectsView.idLabel') }}: <span class="font-mono">{{ project.id.substring(0,8) }}...</span></p> <!-- Reusing from projectsView -->
              <p class="text-xs text-gray-500 mb-3">
                {{ $t('projectsView.createdLabel') }}: {{ project.created_at ? new Date(project.created_at).toLocaleDateString() : $t('common.notAvailable') }} <!-- Reusing from projectsView -->
              </p>
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">
                  {{ $t('homeView.resourcesLabel') }}: {{ project.resources_total !== undefined ? project.resources_total : $t('common.notAvailable') }}
                </span>
                <span class="text-indigo-600 font-medium text-sm">{{ $t('homeView.viewDetailsLink') }} &rarr;</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!isLoadingQuickStats && !quickStatsError" class="text-center py-6 bg-white rounded-lg shadow">
          <p class="text-gray-500">{{ $t('homeView.noProjectsFound') }} <router-link to="/projects" class="text-indigo-600 hover:underline">{{ $t('homeView.createOneLink') }}</router-link></p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles for HomeView if needed */
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
