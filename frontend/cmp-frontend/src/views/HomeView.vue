<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia';

const router = useRouter();
const authStore = useAuthStore();
const { currentUser, isLoggedIn, isAdmin } = storeToRefs(authStore); // Added isAdmin

// --- Projects Data ---
const recentProjects = ref([]);
// isLoadingProjects and projectsError will be replaced by more generic ones for all dashboard data
// const isLoadingProjects = ref(false);
// const projectsError = ref(null);
const MAX_RECENT_PROJECTS = 3; // Display up to 3 recent projects

// --- Quick Stats ---
const quickStats = ref({
  totalProjects: 0,
  activeEc2Instances: 0,
  activeAzureVms: 0,
  totalUsers: null, // Null if not admin or not loaded yet
});
const isLoadingQuickStats = ref(false);
const quickStatsError = ref(null);

const welcomeMessage = computed(() => {
  if (isLoggedIn.value && currentUser.value) {
    return `Welcome back, ${currentUser.value.email}!`;
  }
  return 'Welcome to the CMP Dashboard!';
});

async function fetchDashboardData() {
  isLoadingQuickStats.value = true;
  quickStatsError.value = null;
  recentProjects.value = []; // Clear recent projects before fetching

  let allProjects = [];

  try {
    // 1. Fetch all projects
    const projectsResponse = await apiService.get('/projects');
    allProjects = projectsResponse.data;
    quickStats.value.totalProjects = allProjects.length;

    // Sort and slice for "Recent Projects" display
    const sortedProjects = [...allProjects].sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
    });
    recentProjects.value = sortedProjects.slice(0, MAX_RECENT_PROJECTS);

    // 2. Fetch resources for each project and count active ones
    let ec2Count = 0;
    let azureVmCount = 0;

    const resourcePromises = allProjects.map(async (project) => {
      try {
        const ec2Promise = apiService.get(`/resources/aws/ec2/${project.id}`);
        const azureVmPromise = apiService.get(`/resources/azure/vm/${project.id}`);

        const [ec2Response, azureResponse] = await Promise.all([ec2Promise, azureVmPromise]);

        ec2Response.data.forEach(ec2 => {
          if (ec2.status === 'running') {
            ec2Count++;
          }
        });
        azureResponse.data.forEach(vm => {
          if (vm.status === 'running') { // Corrected condition
            azureVmCount++;
          }
        });
      } catch (projectResourceError) {
        console.warn(`Failed to fetch resources for project ${project.id}:`, projectResourceError);
        // Continue fetching for other projects
      }
    });

    await Promise.all(resourcePromises);
    quickStats.value.activeEc2Instances = ec2Count;
    quickStats.value.activeAzureVms = azureVmCount;

    // 3. Fetch total users if admin
    if (isAdmin.value) {
      try {
        const usersResponse = await apiService.get('/users');
        quickStats.value.totalUsers = usersResponse.data.length;
      } catch (userError) {
        console.error('Failed to fetch total users:', userError);
        // Set to a value indicating error or keep null
        quickStats.value.totalUsers = 'Error'; 
      }
    }

  } catch (err) {
    console.error('Failed to fetch dashboard data:', err);
    quickStatsError.value = err.response?.data?.detail || err.message || 'Could not load dashboard data.';
    // Reset counts on error
    quickStats.value.totalProjects = 0;
    quickStats.value.activeEc2Instances = 0;
    quickStats.value.activeAzureVms = 0;
    if (isAdmin.value) quickStats.value.totalUsers = 'Error';
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
      <p v-if="isLoggedIn" class="text-gray-600">Here's a quick overview of your cloud management activities.</p>
      <p v-else class="text-gray-600">Please log in to manage your cloud resources.</p>

      <!-- Quick Stats Display -->
      <div v-if="isLoggedIn" class="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">Total Projects</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.totalProjects }}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">Active EC2 Instances</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.activeEc2Instances }}</p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">Active Azure VMs</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">{{ isLoadingQuickStats ? '...' : quickStats.activeAzureVms }}</p>
        </div>
        <div v-if="isAdmin" class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-medium text-gray-700">Total Users</h3>
          <p class="text-3xl font-semibold text-indigo-600 mt-1">
            {{ isLoadingQuickStats && quickStats.totalUsers === null ? '...' : (quickStats.totalUsers !== null ? quickStats.totalUsers : 'N/A') }}
          </p>
        </div>
      </div>
      <div v-if="isLoadingQuickStats && !quickStatsError" class="mt-4 text-sm text-gray-500">
        Loading dashboard statistics...
      </div>
      <div v-if="quickStatsError" class="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
        <p>Could not load all dashboard statistics: {{ quickStatsError }}</p>
      </div>
    </section>

    <div v-if="isLoggedIn" class="space-y-8">
      <!-- 2. My Projects / Recent Projects -->
      <section>
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-semibold text-gray-700">Recent Projects</h2>
          <button @click="navigateToProjects" class="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            View All Projects &rarr;
          </button>
        </div>
        <div v-if="isLoadingQuickStats && recentProjects.length === 0" class="text-center py-6">
          <p class="text-gray-500">Loading projects...</p>
        </div>
        <div v-else-if="!isLoadingQuickStats && quickStatsError && recentProjects.length === 0" class="p-4 bg-red-50 text-red-700 rounded-md">
          <!-- Error message for recent projects is covered by the main quickStatsError -->
          <p>Could not load recent projects due to an error.</p>
        </div>
        <div v-else-if="recentProjects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="project in recentProjects" :key="project.id"
               class="bg-white rounded-lg shadow-lg overflow-hidden transform hover:scale-105 transition-transform duration-200 cursor-pointer"
               @click="navigateToProject(project.id)">
            <div class="p-5">
              <h3 class="text-lg font-semibold text-gray-800 mb-2 truncate" :title="project.name">{{ project.name }}</h3>
              <p class="text-xs text-gray-500 mb-1">ID: <span class="font-mono">{{ project.id.substring(0,8) }}...</span></p>
              <p class="text-xs text-gray-500 mb-3">
                Created: {{ project.created_at ? new Date(project.created_at).toLocaleDateString() : 'N/A' }}
              </p>
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">
                  Resources: {{ project.resources_total !== undefined ? project.resources_total : 'N/A' }}
                </span>
                <span class="text-indigo-600 font-medium text-sm">View Details &rarr;</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!isLoadingQuickStats && !quickStatsError" class="text-center py-6 bg-white rounded-lg shadow">
          <p class="text-gray-500">No projects found yet. <router-link to="/projects" class="text-indigo-600 hover:underline">Create one!</router-link></p>
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
