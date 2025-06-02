<template>
  <div class="mt-8">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-semibold text-gray-700">{{ $t('projectMemberManagement.title') }}</h2>
      <div class="text-right">
        <button
          v-if="canManageMembers"
          @click="openAddMemberModal"
          class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          {{ $t('projectMemberManagement.addMemberButton') }}
        </button>
      </div>
    </div>

    <div v-if="isLoadingMembers" class="text-center text-gray-500"><p>{{ $t('projectMemberManagement.loadingMembers') }}</p></div>
    <div v-else-if="membersError" class="text-red-500 p-3 bg-red-100 rounded">
      <p>{{ $t('projectMemberManagement.errorLoadingMembers') }}: {{ membersError.message || $t('common.unknownError') }}</p>
       <p v-if="membersError.response && membersError.response.data && membersError.response.data.detail">
        {{ $t('common.serverErrorPrefix') }}: {{ typeof membersError.response.data.detail === 'string' ? membersError.response.data.detail : JSON.stringify(membersError.response.data.detail) }}
      </p>
    </div>
    <div v-else-if="members.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full border">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('projectMemberManagement.tableHeaderUserEmail') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('projectMemberManagement.tableHeaderUserId') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('projectMemberManagement.tableHeaderRole') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="member in membersWithDetails" :key="member.user_id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.email || $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.user_id }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ member.role_id ? $t(`roles.${member.role_id.toLowerCase()}`) : $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="canManageMembers"
                @click="openEditMemberModal(member)"
                class="text-yellow-600 hover:text-yellow-900"
              >
                {{ $t('common.edit') }}
              </button>
              <button
                v-if="canManageMembers && member.user_id !== projectOwnerId && member.user_id !== authStore.currentUser?.id"
                @click="openDeleteMemberModal(member)"
                class="text-red-600 hover:text-red-900"
              >
                {{ $t('projectMemberManagement.removeButton') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-gray-500 text-center py-4"><p>{{ $t('projectMemberManagement.noMembersFound') }}</p></div>

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
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">{{ $t('projectMemberManagement.addModal.title') }}</h3>
          <form @submit.prevent="submitAddMember" class="mt-4 space-y-4">
            <div v-if="memberModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || $t('common.couldNotProcessRequest') }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                {{ $t('common.serverErrorPrefix') }}: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
            <div>
              <label for="newMemberUser" class="block text-sm font-medium text-gray-700">{{ $t('projectMemberManagement.addModal.userLabel') }}</label>
              <select id="newMemberUser" v-model="newMember.user_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option disabled value="">{{ $t('projectMemberManagement.addModal.selectUserPlaceholder') }}</option>
                <option v-for="user in availableUsers" :key="user.id" :value="user.id">{{ user.email }} ({{ user.id }})</option>
              </select>
            </div>
            <div>
              <label for="newMemberRole" class="block text-sm font-medium text-gray-700">{{ $t('projectMemberManagement.addModal.roleLabel') }}</label>
              <select id="newMemberRole" v-model="newMember.role_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option value="viewer">{{ $t('roles.viewer') }}</option>
                <option value="devops">{{ $t('roles.devops') }}</option>
              </select>
            </div>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeAddMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
              <button type="submit" :disabled="isProcessingMember" class="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-green-300">
                <span v-if="isProcessingMember">{{ $t('projectMemberManagement.addModal.addingButton') }}</span>
                <span v-else>{{ $t('projectMemberManagement.addModal.addMemberButtonText') }}</span>
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
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">{{ $t('projectMemberManagement.editModal.title') }}</h3>
          <form @submit.prevent="submitEditMember" class="mt-4 space-y-4">
             <div v-if="memberModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || $t('common.couldNotProcessRequest') }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                {{ $t('common.serverErrorPrefix') }}: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
            <p class="text-sm text-gray-700">{{ $t('projectMemberManagement.editModal.editingRoleForLabel', { user: editingMember?.email || editingMember?.user_id }) }}</p>
            <div>
              <label for="editMemberRole" class="block text-sm font-medium text-gray-700">{{ $t('projectMemberManagement.editModal.newRoleLabel') }}</label>
              <select id="editMemberRole" v-model="editingMember.role_id" required class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                <option value="viewer">{{ $t('roles.viewer') }}</option>
                <option value="devops">{{ $t('roles.devops') }}</option>
              </select>
            </div>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeEditMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
              <button type="submit" :disabled="isProcessingMember" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                <span v-if="isProcessingMember">{{ $t('common.saving') }}</span>
                <span v-else>{{ $t('common.saveChanges') }}</span>
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
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">{{ $t('projectMemberManagement.deleteModal.title') }}</h3>
          <div class="mt-2 px-7 py-3">
            <p class="text-sm text-gray-600" v-html="$t('projectMemberManagement.deleteModal.confirmationText', { user: memberToDelete?.email || memberToDelete?.user_id })"></p>
            <div v-if="memberModalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ memberModalError.message || $t('common.couldNotProcessRequest') }}</p>
              <p v-if="memberModalError.response && memberModalError.response.data && memberModalError.response.data.detail">
                {{ $t('common.serverErrorPrefix') }}: {{ typeof memberModalError.response.data.detail === 'string' ? memberModalError.response.data.detail : JSON.stringify(memberModalError.response.data.detail) }}
              </p>
            </div>
          </div>
          <div class="items-center px-4 py-3 space-x-4 flex justify-end">
            <button type="button" @click="closeDeleteMemberModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
            <button @click="submitDeleteMember" :disabled="isProcessingMember" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
              <span v-if="isProcessingMember">{{ $t('projectMemberManagement.deleteModal.removingButton') }}</span>
              <span v-else>{{ $t('projectMemberManagement.deleteModal.removeMemberButtonText') }}</span>
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
import { useAuthStore } from '@/stores/auth';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  projectOwnerId: {
    type: String,
    required: true
  },
  allUsersForProject: {
    type: Array,
    required: true
  },
  canManageMembers: {
    type: Boolean,
    required: true
  }
});

const authStore = useAuthStore();

const members = ref([]);
const isLoadingMembers = ref(false);
const membersError = ref(null);

const memberModalError = ref(null);
const isProcessingMember = ref(false);

const showAddMemberModal = ref(false);
const newMember = ref({ user_id: '', role_id: 'viewer' });

const showEditMemberModal = ref(false);
const editingMember = ref(null);

const showDeleteMemberModal = ref(false);
const memberToDelete = ref(null);

const membersWithDetails = computed(() => {
  return members.value.map(member => {
    const user = props.allUsersForProject.find(u => u.id === member.user_id);
    return {
      ...member,
      email: user ? user.email : t('projectMemberManagement.unknownUser')
    };
  });
});

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
    memberModalError.value = { message: t('projectMemberManagement.addModal.userAndRoleRequiredError') };
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

function openEditMemberModal(member) {
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
    memberModalError.value = { message: t('projectMemberManagement.editModal.roleIsRequiredError') };
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

function openDeleteMemberModal(member) {
  memberToDelete.value = { ...member };
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
    await fetchProjectMembers();
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