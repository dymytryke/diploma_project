<template>
  <div class="p-4 sm:p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold text-gray-800">Projects</h1>
      <button
        v-if="authStore.isDevops || authStore.isAdmin"
        @click="openCreateModal"
        class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
      >
        Create New Project
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !projects.length" class="text-center text-gray-500 mt-10">
      <p>Loading projects...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center text-red-500 mt-10 p-4 bg-red-100 rounded">
      <p>Error loading projects: {{ error.message || 'Unknown error' }}</p>
      <p v-if="error.response && error.response.data && error.response.data.detail">
        Server says: {{ typeof error.response.data.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response.data.detail) }}
      </p>
      <button @click="fetchProjects" class="mt-2 bg-blue-500 hover:bg-blue-600 text-white py-1 px-3 rounded">
        Retry
      </button>
    </div>

    <!-- Project List -->
    <div v-else-if="projects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="project in projects" :key="project.id" class="bg-white rounded-lg shadow-lg overflow-hidden">
        <div class="p-6">
          <h2 class="text-xl font-semibold text-gray-700 mb-2">{{ project.name }}</h2>
          <p class="text-gray-600 text-sm mb-1"><strong>ID:</strong> {{ project.id }}</p>
          <p class="text-gray-600 text-sm mb-1"><strong>Owner ID:</strong> {{ project.owner_id }}</p>
          <p class="text-gray-600 text-sm mb-1">
            <strong>Created:</strong> {{ project.created_at ? new Date(project.created_at).toLocaleDateString() : 'N/A' }}
          </p>
          <p class="text-gray-600 text-sm mb-4">
            <strong>Total Resources:</strong> {{ project.resources_total !== undefined ? project.resources_total : 'N/A' }}
          </p>
          <div class="mt-4 flex justify-end space-x-2">
            <button @click="viewProject(project.id)" class="text-sm bg-blue-500 hover:bg-blue-600 text-white py-1 px-3 rounded">
              View
            </button>
            <button
              v-if="authStore.isDevops || authStore.isAdmin"
              @click="openEditModal(project)"
              class="text-sm bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded"
            >
              Edit
            </button>
            <button
              v-if="authStore.isDevops || authStore.isAdmin"
              @click="openDeleteModal(project)"
              class="text-sm bg-red-500 hover:bg-red-600 text-white py-1 px-3 rounded"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- No Projects Found -->
    <div v-else-if="!isLoading" class="text-center text-gray-500 mt-10">
      <p>No projects found. Start by creating a new one!</p>
    </div>

    <!-- Create Project Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Create New Project</h3>
            <form @submit.prevent="submitCreateProject" class="mt-2 px-7 py-3">
              <div v-if="createProjectError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>Error: {{ createProjectError.message || 'Could not create project.' }}</p>
                <p v-if="createProjectError.response && createProjectError.response.data && createProjectError.response.data.detail">
                  Server: {{ typeof createProjectError.response.data.detail === 'string' ? createProjectError.response.data.detail : JSON.stringify(createProjectError.response.data.detail) }}
                </p>
              </div>
              <div class="mb-4">
                <label for="projectName" class="block text-sm font-medium text-gray-700 text-left">Project Name</label>
                <input
                  type="text"
                  id="projectName"
                  v-model="newProjectName"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="My Awesome Project"
                />
              </div>
              <div class="items-center px-4 py-3 space-x-4 flex justify-end">
                <button
                  type="button"
                  @click="closeCreateModal"
                  class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  :disabled="isCreatingProject"
                  class="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-green-300"
                >
                  <span v-if="isCreatingProject">Creating...</span>
                  <span v-else>Create</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit Project Modal -->
    <Teleport to="body">
      <div v-if="showEditModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Edit Project</h3>
            <form @submit.prevent="submitEditProject" class="mt-2 px-7 py-3">
              <div v-if="editProjectError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>Error: {{ editProjectError.message || 'Could not update project.' }}</p>
                <p v-if="editProjectError.response && editProjectError.response.data && editProjectError.response.data.detail">
                  Server: {{ typeof editProjectError.response.data.detail === 'string' ? editProjectError.response.data.detail : JSON.stringify(editProjectError.response.data.detail) }}
                </p>
              </div>
              <div class="mb-4">
                <label for="editProjectName" class="block text-sm font-medium text-gray-700 text-left">New Project Name</label>
                <input
                  type="text"
                  id="editProjectName"
                  v-model="editProjectNameInput"
                  required
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="Updated Project Name"
                />
              </div>
              <div class="items-center px-4 py-3 space-x-4 flex justify-end">
                <button
                  type="button"
                  @click="closeEditModal"
                  class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  :disabled="isEditingProject"
                  class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:bg-yellow-300"
                >
                  <span v-if="isEditingProject">Saving...</span>
                  <span v-else>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Project Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Delete Project</h3>
            <div class="mt-2 px-7 py-3">
              <p class="text-sm text-gray-500">
                Are you sure you want to delete the project "<strong>{{ projectToDelete?.name }}</strong>"?
                This action cannot be undone.
              </p>
              <div v-if="deleteProjectError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>Error: {{ deleteProjectError.message || 'Could not delete project.' }}</p>
                <p v-if="deleteProjectError.response && deleteProjectError.response.data && deleteProjectError.response.data.detail">
                  Server: {{ typeof deleteProjectError.response.data.detail === 'string' ? deleteProjectError.response.data.detail : JSON.stringify(deleteProjectError.response.data.detail) }}
                </p>
              </div>
            </div>
            <div class="items-center px-4 py-3 space-x-4 flex justify-end">
              <button
                type="button"
                @click="closeDeleteModal"
                class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                @click="submitDeleteProject"
                :disabled="isDeletingProject"
                class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:bg-red-400"
              >
                <span v-if="isDeletingProject">Deleting...</span>
                <span v-else>Delete Project</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, Teleport } from 'vue'; // Keep Teleport if modals are still in this file
import { useRouter } from 'vue-router';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const projects = ref([]);
const isLoading = ref(false);
const error = ref(null);

// State for Create Project Modal
const showCreateModal = ref(false);
const newProjectName = ref('');
const createProjectError = ref(null);
const isCreatingProject = ref(false);

// State for Edit Project Modal
const showEditModal = ref(false);
const editingProject = ref(null);
const editProjectNameInput = ref('');
const editProjectError = ref(null);
const isEditingProject = ref(false);

// State for Delete Project Modal
const showDeleteModal = ref(false);
const projectToDelete = ref(null);
const deleteProjectError = ref(null);
const isDeletingProject = ref(false);


async function fetchProjects() {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await apiService.get('/projects');
    projects.value = response.data;
  } catch (err) {
    console.error('Failed to fetch projects:', err.response?.data || err.message);
    error.value = err;
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  fetchProjects();
});

// --- Create Project Modal Functions ---
function openCreateModal() {
  newProjectName.value = '';
  createProjectError.value = null;
  showCreateModal.value = true;
  console.log('Attempting to open Create Modal. showCreateModal:', showCreateModal.value);
}

function closeCreateModal() {
  showCreateModal.value = false;
}

async function submitCreateProject() {
  if (!newProjectName.value.trim()) {
    createProjectError.value = { message: 'Project name cannot be empty.' };
    return;
  }
  isCreatingProject.value = true;
  createProjectError.value = null;
  try {
    const response = await apiService.post('/projects', { name: newProjectName.value });
    projects.value.push(response.data);
    closeCreateModal();
  } catch (err) {
    console.error('Failed to create project:', err.response?.data || err.message);
    createProjectError.value = err;
  } finally {
    isCreatingProject.value = false;
  }
}

// --- Edit Project Modal Functions ---
function openEditModal(project) {
  editingProject.value = project;
  editProjectNameInput.value = project.name;
  editProjectError.value = null;
  showEditModal.value = true;
  console.log('Attempting to open Edit Modal. showEditModal:', showEditModal.value);
}

function closeEditModal() {
  showEditModal.value = false;
  editingProject.value = null;
}

async function submitEditProject() {
  if (!editingProject.value || !editProjectNameInput.value.trim()) {
    editProjectError.value = { message: 'Project name cannot be empty.' };
    return;
  }
  isEditingProject.value = true;
  editProjectError.value = null;
  try {
    const response = await apiService.patch(`/projects/${editingProject.value.id}`, { name: editProjectNameInput.value });
    const index = projects.value.findIndex(p => p.id === editingProject.value.id);
    if (index !== -1) {
      projects.value[index] = response.data;
    }
    closeEditModal();
  } catch (err) {
    console.error('Failed to update project:', err.response?.data || err.message);
    editProjectError.value = err;
  } finally {
    isEditingProject.value = false;
  }
}

// --- Delete Project Modal Functions ---
function openDeleteModal(project) {
  projectToDelete.value = project;
  deleteProjectError.value = null;
  showDeleteModal.value = true;
  console.log('Attempting to open Delete Modal. showDeleteModal:', showDeleteModal.value);
}

function closeDeleteModal() {
  showDeleteModal.value = false;
  projectToDelete.value = null;
}

async function submitDeleteProject() {
  if (!projectToDelete.value) return;

  isDeletingProject.value = true;
  deleteProjectError.value = null;
  try {
    await apiService.delete(`/projects/${projectToDelete.value.id}`);
    projects.value = projects.value.filter(p => p.id !== projectToDelete.value.id);
    closeDeleteModal();
  } catch (err) {
    console.error('Failed to delete project:', err.response?.data || err.message);
    deleteProjectError.value = err;
  } finally {
    isDeletingProject.value = false;
  }
}

function viewProject(projectIdValue) { // Parameter passed is the actual project ID
  router.push({ name: 'project-detail', params: { projectId: projectIdValue } }); 
}
</script>

<style scoped>
/* Styles for ProjectsView component */
</style>