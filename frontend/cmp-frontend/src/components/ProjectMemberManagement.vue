<template>
  <div class="mt-8">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-semibold text-gray-700">Project Members</h2>
      <div class="text-right">
        <button
          v-if="canManageMembers"
          @click="openAddMemberModal"
          class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          Add Member
        </button>
      </div>
    </div>

    <div v-if="isLoadingMembers" class="text-center text-gray-500"><p>Loading members...</p></div>
    <div v-else-if="membersError" class="text-red-500 p-3 bg-red-100 rounded">
      <p>Error loading members: {{ membersError.message || 'Unknown error' }}</p>
       <p v-if="membersError.response && membersError.response.data && membersError.response.data.detail">
        Server: {{ typeof membersError.response.data.detail === 'string' ? membersError.response.data.detail : JSON.stringify(membersError.response.data.detail) }}
      </p>
    </div>
    <div v-else-if="members.length > 0" class="overflow-x-auto">
      <table class="min-w-full bg-white border">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User Email</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="member in membersWithDetails" :key="member.user_id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.email || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.user_id }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.role_id }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="canManageMembers"
                @click="openEditMemberModal(member)"
                class="text-yellow-600 hover:text-yellow-900"
              >
                Edit
              </button>
              <button
                v-if="canManageMembers && member.user_id !== projectOwnerId && member.user_id !== authStore.currentUser?.id"
                @click="openDeleteMemberModal(member)"
                class="text-red-600 hover:text-red-900"
              >
                Remove
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-gray-500 text-center py-4"><p>No members found for this project.</p></div>

    <!-- Add Member Modal -->
    <Teleport to="body">
      <div v-if="showAddMemberModal" 
                 style="position: fixed !important;
                  inset: 0px !important;
                  background-color: rgba(75, 85, 99, 0.5) !important; /* bg-gray-600 bg-opacity-50 */
                  z-index: 50 !important; 
                  display: flex !important;
                  align-items: center !important;
                  justify-content: center !important;
                  opacity: 1 !important;
                  visibility: visible !important;
                  overflow-y: auto !important; 
                  height: 100% !important; 
                  width: 100% !important;"
           class=""
      >
        <div class="relative mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">Add New Member</h3>
          <form @submit.prevent="submitAddMember" class="mt-4 space-y-4">
            <div v-if="memberModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || 'Could not process request.' }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                Server: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
            <div>
              <label for="newMemberUser" class="block text-sm font-medium text-gray-700">User</label>
              <select id="newMemberUser" v-model="newMember.user_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option disabled value="">Select a user</option>
                <option v-for="user in availableUsers" :key="user.id" :value="user.id">{{ user.email }} ({{ user.id }})</option>
              </select>
            </div>
            <div>
              <label for="newMemberRole" class="block text-sm font-medium text-gray-700">Role</label>
              <select id="newMemberRole" v-model="newMember.role_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option value="viewer">Viewer</option>
                <option value="devops">DevOps</option>
              </select>
            </div>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeAddMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
              <button type="submit" :disabled="isProcessingMember" class="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-green-300">
                <span v-if="isProcessingMember">Adding...</span>
                <span v-else>Add Member</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit Member Modal -->
    <Teleport to="body">
      <div v-if="showEditMemberModal" 
                 style="position: fixed !important;
                  inset: 0px !important;
                  background-color: rgba(75, 85, 99, 0.5) !important; /* bg-gray-600 bg-opacity-50 */
                  z-index: 50 !important; 
                  display: flex !important;
                  align-items: center !important;
                  justify-content: center !important;
                  opacity: 1 !important;
                  visibility: visible !important;
                  overflow-y: auto !important; 
                  height: 100% !important; 
                  width: 100% !important;"
           class=""
      >
        <div class="relative mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">Edit Member Role</h3>
          <form @submit.prevent="submitEditMember" class="mt-4 space-y-4">
             <div v-if="memberModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || 'Could not process request.' }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                Server: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
            <p class="text-sm text-gray-700">Editing role for: <strong>{{ editingMember?.email || editingMember?.user_id }}</strong></p>
            <div>
              <label for="editMemberRole" class="block text-sm font-medium text-gray-700">New Role</label>
              <select id="editMemberRole" v-model="editingMember.role_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option value="viewer">Viewer</option>
                <option value="devops">DevOps</option>
              </select>
            </div>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeEditMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
              <button type="submit" :disabled="isProcessingMember" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                <span v-if="isProcessingMember">Saving...</span>
                <span v-else>Save Changes</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Member Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteMemberModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center z-50">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">Remove Project Member</h3>
          <div class="mt-2 px-7 py-3">
            <p class="text-sm text-gray-600">
              Are you sure you want to remove <strong class="text-gray-800">{{ memberToDelete?.email || memberToDelete?.user_id }}</strong> from this project?
            </p>
            <div v-if="memberModalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || 'Could not process request.' }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                Server: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
          </div>
          <div class="items-center px-4 py-3 space-x-4 flex justify-end">
            <button type="button" @click="closeDeleteMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
            <button @click="submitDeleteMember" :disabled="isProcessingMember" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
              <span v-if="isProcessingMember">Removing...</span>
              <span v-else>Remove Member</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import apiService from '@/services/api';
import { useAuthStore } from '@/stores/auth'; // Needed for current user check

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  projectOwnerId: { // To prevent removing owner
    type: String,
    required: true
  },
  allUsersForProject: { // Pass all users for the dropdown
    type: Array,
    required: true
  },
  canManageMembers: { // Combined permission prop (isDevops || isAdmin || isOwner)
    type: Boolean,
    required: true
  }
});

const authStore = useAuthStore();

const members = ref([]);
const isLoadingMembers = ref(false);
const membersError = ref(null);

// --- Member Modal State (Common) ---
const memberModalError = ref(null);
const isProcessingMember = ref(false);

// --- Add Member Modal State ---
const showAddMemberModal = ref(false);
const newMember = ref({ user_id: '', role_id: 'viewer' });

// --- Edit Member Modal State ---
const showEditMemberModal = ref(false);
const editingMember = ref(null); // Will store { user_id, email, role_id }

// --- Delete Member Modal State ---
const showDeleteMemberModal = ref(false);
const memberToDelete = ref(null); // Will store { user_id, email }

// --- Computed property to enrich members with user details (email) ---
const membersWithDetails = computed(() => {
  return members.value.map(member => {
    const user = props.allUsersForProject.find(u => u.id === member.user_id);
    return {
      ...member,
      email: user ? user.email : 'Unknown User'
    };
  });
});

// --- Computed property for available users (not already members and not the project owner) ---
const availableUsers = computed(() => {
  if (!props.projectId) return [];
  return props.allUsersForProject.filter(user =>
    !members.value.some(member => member.user_id === user.id) &&
    user.id !== props.projectOwnerId
  );
});

async function fetchProjectMembers() {
  if (!props.projectId) return;
  isLoadingMembers.value = true;
  membersError.value = null;
  try {
    const response = await apiService.get(`/projects/${props.projectId}/members`);
    members.value = response.data;
  } catch (err) {
    console.error('Failed to fetch project members:', err);
    membersError.value = err.response?.data || err;
  } finally {
    isLoadingMembers.value = false;
  }
}

onMounted(() => {
  if (props.projectId) {
    fetchProjectMembers();
  }
});

watch(() => props.projectId, (newProjectId) => {
  if (newProjectId) {
    fetchProjectMembers();
  } else {
    members.value = [];
  }
});

// --- Add Member Modal Functions ---
function openAddMemberModal() {
  newMember.value = { user_id: '', role_id: 'viewer' };
  memberModalError.value = null;
  showAddMemberModal.value = true;
}

function closeAddMemberModal() {
  showAddMemberModal.value = false;
}

async function submitAddMember() {
  if (!newMember.value.user_id || !newMember.value.role_id) {
    memberModalError.value = { message: 'User and Role are required.' };
    return;
  }
  isProcessingMember.value = true;
  memberModalError.value = null;
  try {
    await apiService.post(`/projects/${props.projectId}/members`, newMember.value);
    await fetchProjectMembers();
    closeAddMemberModal();
  } catch (err) {
    console.error('Failed to add member:', err);
    memberModalError.value = err.response?.data || err;
  } finally {
    isProcessingMember.value = false;
  }
}

// --- Edit Member Modal Functions ---
function openEditMemberModal(member) {
  // member here is from membersWithDetails, so it includes email
  editingMember.value = { user_id: member.user_id, role_id: member.role_id, email: member.email };
  memberModalError.value = null;
  showEditMemberModal.value = true;
}

function closeEditMemberModal() {
  showEditMemberModal.value = false;
  editingMember.value = null;
}

async function submitEditMember() {
  if (!editingMember.value || !editingMember.value.role_id) {
    memberModalError.value = { message: 'Role is required.' };
    return;
  }
  isProcessingMember.value = true;
  memberModalError.value = null;
  try {
    const payload = { role_id: editingMember.value.role_id };
    await apiService.patch(`/projects/${props.projectId}/members/${editingMember.value.user_id}`, payload);
    await fetchProjectMembers();
    closeEditMemberModal();
  } catch (err) {
    console.error('Failed to update member role:', err);
    memberModalError.value = err.response?.data || err;
  } finally {
    isProcessingMember.value = false;
  }
}

// --- Delete Member Modal Functions ---
function openDeleteMemberModal(member) {
  memberToDelete.value = { ...member }; // Store the member to be deleted
  memberModalError.value = null;
  showDeleteMemberModal.value = true;
}

function closeDeleteMemberModal() {
  showDeleteMemberModal.value = false;
  memberToDelete.value = null;
}

async function submitDeleteMember() {
  if (!memberToDelete.value) return;

  isProcessingMember.value = true;
  memberModalError.value = null;
  try {
    await apiService.delete(`/projects/${props.projectId}/members/${memberToDelete.value.user_id}`);
    await fetchProjectMembers(); // Re-fetch to update the list
    closeDeleteMemberModal();
  } catch (err) {
    console.error('Failed to remove member:', err);
    memberModalError.value = err.response?.data || err;
  } finally {
    isProcessingMember.value = false;
  }
}
</script>

<style scoped>
/* Scoped styles for ProjectMemberManagement */
</style>