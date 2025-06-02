<template>
  <div class="p-4 sm:p-6">
    <!-- Loading State -->
    <div v-if="isLoadingProject && !project" class="text-center text-gray-500 mt-10">
      <p>{{ $t('projectDetailView.loadingDetails') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="projectError" class="text-center text-red-500 mt-10 p-4 bg-red-100 rounded">
      <p>{{ $t('projectDetailView.errorLoadingProject') }}: {{ projectError.message || $t('common.unknownError') }}</p>
      <p v-if="projectError.response && projectError.response.data && projectError.response.data.detail">
        {{ $t('common.serverErrorPrefix') }}: {{ typeof projectError.response.data.detail === 'string' ? projectError.response.data.detail : JSON.stringify(projectError.response.data.detail) }}
      </p>
      <router-link to="/projects" class="mt-4 inline-block bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
        {{ $t('projectDetailView.backToProjects') }}
      </router-link>
    </div>

    <!-- Project Details -->
    <div v-else-if="project" class="bg-white shadow-lg rounded-lg p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-800">{{ project.name }}</h1>
        <router-link to="/projects" class="text-sm bg-gray-200 hover:bg-gray-300 text-gray-700 py-1 px-3 rounded">
          {{ $t('projectDetailView.backToProjects') }}
        </router-link>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <p><strong class="text-gray-600">{{ $t('projectsView.idLabel') }}:</strong> {{ project.id }}</p>
        <p><strong class="text-gray-600">{{ $t('projectsView.ownerIdLabel') }}:</strong> {{ project.owner_id }}</p>
        <p><strong class="text-gray-600">{{ $t('projectsView.createdLabel') }}:</strong> {{ project.created_at ? new Date(project.created_at).toLocaleString() : $t('common.notAvailable') }}</p>
        <p><strong class="text-gray-600">{{ $t('projectsView.totalResourcesLabel') }}:</strong> {{ project.resources_total !== undefined ? project.resources_total : $t('common.notAvailable') }}</p>
      </div>

      <!-- Project Members Section - Replaced with component -->
      <!-- Only show if admin is viewing -->
      <ProjectMemberManagement
        v-if="project && props.projectId && authStore.isAdmin"
        :project-id="props.projectId"
        :project-owner-id="project.owner_id"
        :all-users-for-project="allUsers"
        :can-manage-members="canManageProjectMembers"
      />

      <!-- AWS EC2 Instances Section -->
      <Ec2InstanceManagement
        v-if="project && props.projectId"
        :project-id="props.projectId"
        :can-manage-ec2="canManageEc2ForProject"
      />

      <!-- Azure Virtual Machines Section -->
      <AzureVmManagement
        v-if="project && props.projectId"
        :project-id="props.projectId"
        :can-manage-azure-vms="canManageAzureVmsForProject"
      />

    </div>
    <div v-else-if="!isLoadingProject" class="text-center text-gray-500 mt-10">
      <p>{{ $t('projectDetailView.projectNotFound') }}</p>
      <router-link to="/projects" class="mt-4 inline-block bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
        {{ $t('projectDetailView.backToProjects') }}
      </router-link>
    </div>

    <!-- REMOVE all Member Modals from here -->
    <!-- They are now inside ProjectMemberManagement.vue -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed, defineProps } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import Ec2InstanceManagement from '@/components/Ec2InstanceManagement.vue';
import ProjectMemberManagement from '@/components/ProjectMemberManagement.vue';
import AzureVmManagement from '@/components/AzureVmManagement.vue';
import { useI18n } from 'vue-i18n'; // Import useI18n

const { t } = useI18n(); // Initialize t function

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
});

const project = ref(null);
const isLoadingProject = ref(false);
const projectError = ref(null);

const allUsers = ref([]);
const isLoadingUsers = ref(false);
const usersError = ref(null);

const isOwner = computed(() => {
  return project.value && authStore.currentUser && project.value.owner_id === authStore.currentUser.id;
});

const canManageEc2ForProject = computed(() => {
  return authStore.isDevops || authStore.isAdmin || isOwner.value;
});

const canManageAzureVmsForProject = computed(() => {
  return authStore.isDevops || authStore.isAdmin || isOwner.value;
});

const canManageProjectMembers = computed(() => {
  return authStore.isDevops || authStore.isAdmin || isOwner.value;
});

async function fetchProjectDetails() {
  if (!props.projectId) return;
  isLoadingProject.value = true;
  projectError.value = null;
  try {
    const response = await apiService.get(`/projects/${props.projectId}`);
    project.value = response.data;
    await fetchAllUsers();
  } catch (err) {
    console.error('Failed to fetch project details:', err);
    projectError.value = err.response?.data || err;
    project.value = null;
  } finally {
    isLoadingProject.value = false;
  }
}

async function fetchAllUsers() {
  isLoadingUsers.value = true;
  usersError.value = null;
  try {
    const response = await apiService.get('/users');
    allUsers.value = response.data;
  } catch (err) {
    console.error('Failed to fetch all users:', err);
    usersError.value = err.response?.data || err;
  } finally {
    isLoadingUsers.value = false;
  }
}

onMounted(() => {
  fetchProjectDetails();
});

</script>

<style scoped>
/* Scoped styles for ProjectDetailView */
</style>