<template>
  <div class="mt-10 pt-6 border-t">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-semibold text-gray-700">Azure Virtual Machines</h2>
      <div class="space-x-2">
        <button
          @click="handleRefreshAzureVms"
          :disabled="isLoadingAzureVms"
          class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-300"
        >
          <span v-if="isLoadingAzureVms && !isProcessingActionAzureVmId">Refreshing...</span>
          <span v-else>Refresh List</span>
        </button>
        <button
          v-if="canManageAzureVms"
          @click="openAddAzureVmModal"
          class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          Add Azure VM
        </button>
      </div>
    </div>

    <!-- Loading Azure VMs -->
    <div v-if="isLoadingAzureVms" class="text-center text-gray-500">
      <p>Loading Azure VMs...</p>
    </div>
    <!-- Error Loading Azure VMs -->
    <div v-else-if="azureVmsError" class="text-red-500 p-3 bg-red-100 rounded">
      <p>Error loading Azure VMs: {{ azureVmsError.message || 'Unknown error' }}</p>
      <p v-if="azureVmsError.response && azureVmsError.response.data && azureVmsError.response.data.detail">
        Server: {{ typeof azureVmsError.response.data.detail === 'string' ? azureVmsError.response.data.detail : JSON.stringify(azureVmsError.response.data.detail) }}
      </p>
    </div>
    <!-- Azure VMs Table -->
    <div v-else-if="azureVms.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name (CMP)</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Region</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM Size</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Public IP</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resource Group</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="vm in azureVms" :key="vm.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.name }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.region }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.vm_size || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <span :class="getStatusClass(vm.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                {{ vm.status }}
              </span>
              <span v-if="isProcessingActionAzureVmId === vm.name" class="ml-2 text-xs text-gray-500">({{ azureVmActionInProgress }})</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.public_ip || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.resource_group || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="canViewDashboard(vm) && canManageAzureVms"
                @click="openGrafanaDashboard(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-blue-600 hover:text-blue-900 disabled:text-gray-400"
                title="View Dashboard"
              >
                Dashboard
              </button>
              <button
                v-if="canEditVm(vm) && canManageAzureVms"
                @click="openEditAzureVmModal(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-yellow-600 hover:text-yellow-900 disabled:text-gray-400"
              >
                Edit
              </button>
              <button
                v-if="canStartVm(vm) && canManageAzureVms"
                @click="startAzureVm(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-green-600 hover:text-green-900 disabled:text-gray-400"
              >
                Start
              </button>
              <button
                v-if="canStopVm(vm) && canManageAzureVms"
                @click="stopAzureVm(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
              >
                Stop
              </button>
              <button
                v-if="canDeleteVm(vm) && canManageAzureVms"
                @click="openDeleteAzureVmModal(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-red-600 hover:text-red-900 disabled:text-gray-400"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-gray-500 text-center py-4">
      <p>No Azure VMs found for this project.</p>
    </div>

    <!-- Add Azure VM Modal -->
    <Teleport to="body">
      <div v-if="showAddAzureVmModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto w-full h-full">
        <div
          class="relative mx-auto p-5 border w-full max-w-xl shadow-lg rounded-md bg-white"> 
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center mb-4">Add New Azure Virtual Machine</h3>
          <form @submit.prevent="submitAddAzureVm" class="space-y-4 max-h-[80vh] overflow-y-auto px-2">
            <div v-if="azureVmModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ azureVmModalError.message || 'Could not process request.' }}</p>
              <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                Server: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
              </p>
            </div>

            <div>
              <label for="azureVmName" class="block text-sm font-medium text-gray-700">Name (CMP Internal)</label>
              <input type="text" id="azureVmName" v-model="newAzureVm.name" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <div>
              <label for="azureVmRegion" class="block text-sm font-medium text-gray-700">Region</label>
              <select id="azureVmRegion" v-model="newAzureVm.region" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="region in azureRegions" :key="region" :value="region">{{ region }}</option>
              </select>
            </div>
            <div>
              <label for="azureVmSize" class="block text-sm font-medium text-gray-700">VM Size</label>
              <select id="azureVmSize" v-model="newAzureVm.vm_size" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="size in azureVmSizes" :key="size" :value="size">{{ size }}</option>
              </select>
            </div>
            <div>
              <label for="azureVmAdminUsername" class="block text-sm font-medium text-gray-700">Admin Username</label>
              <input type="text" id="azureVmAdminUsername" v-model="newAzureVm.admin_username" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <div>
              <label for="azureVmAdminPassword" class="block text-sm font-medium text-gray-700">Admin Password</label>
              <input type="password" id="azureVmAdminPassword" v-model="newAzureVm.admin_password" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>

            <fieldset class="border p-4 rounded-md">
              <legend class="text-sm font-medium text-gray-700 px-1">Image Reference (Ensure compatibility with Region/VM Size)</legend>
              <!-- Image reference fields remain text for now due to complexity -->
              <div class="space-y-3">
                <div>
                  <label for="azureVmImgPublisher" class="block text-xs font-medium text-gray-600">Publisher</label>
                  <input type="text" id="azureVmImgPublisher" v-model="newAzureVm.image_reference.publisher" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgOffer" class="block text-xs font-medium text-gray-600">Offer</label>
                  <input type="text" id="azureVmImgOffer" v-model="newAzureVm.image_reference.offer" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgSku" class="block text-xs font-medium text-gray-600">SKU</label>
                  <input type="text" id="azureVmImgSku" v-model="newAzureVm.image_reference.sku" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgVersion" class="block text-xs font-medium text-gray-600">Version</label>
                  <input type="text" id="azureVmImgVersion" v-model="newAzureVm.image_reference.version" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
              </div>
            </fieldset>
            
            <details class="border p-2 rounded-md">
                <summary class="text-sm font-medium text-gray-700 cursor-pointer">Advanced Network Options</summary>
                <div class="mt-2 space-y-3 p-2">
                    <div>
                        <label for="azureVmVnetPrefix" class="block text-xs font-medium text-gray-600">VNet Address Prefix (e.g., 10.0.0.0/16)</label>
                        <input type="text" id="azureVmVnetPrefix" v-model="newAzureVm.vnet_address_prefix" placeholder="Default: 10.0.0.0/16" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                    </div>
                    <div>
                        <label for="azureVmSubnetPrefix" class="block text-xs font-medium text-gray-600">Subnet Prefix (e.g., 10.0.1.0/24)</label>
                        <input type="text" id="azureVmSubnetPrefix" v-model="newAzureVm.subnet_prefix" placeholder="Default: 10.0.1.0/24" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                    </div>
                    <div>
                        <label for="azureVmPublicIpAlloc" class="block text-xs font-medium text-gray-600">Public IP Allocation</label>
                        <select id="azureVmPublicIpAlloc" v-model="newAzureVm.public_ip_allocation_method" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                            <option value="Dynamic">Dynamic</option>
                            <option value="Static">Static</option>
                        </select>
                    </div>
                </div>
            </details>


            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeAddAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
              <button type="submit" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:bg-purple-300">
                <span v-if="isProcessingAzureVm">Adding...</span>
                <span v-else>Add VM</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
    
    <!-- Edit Azure VM Modal -->
     <Teleport to="body">
      <div v-if="showEditAzureVmModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto w-full h-full"> 
        <div
          class="relative mx-auto p-5 border w-full max-w-xl shadow-lg rounded-md bg-white"> 
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center mb-4">Edit Azure VM: {{ editingAzureVm?.name }}</h3>
          <form @submit.prevent="submitEditAzureVm" class="space-y-4">
            <div v-if="azureVmModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ azureVmModalError.message || 'Could not process request.' }}</p>
              <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                Server: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
              </p>
            </div>
            <div>
              <label for="editAzureVmSize" class="block text-sm font-medium text-gray-700">New VM Size</label>
              <select id="editAzureVmSize" v-model="editingAzureVm.vm_size" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="size in azureVmSizes" :key="size" :value="size">{{ size }}</option>
              </select>
              <p class="mt-1 text-xs text-gray-500">Current size: {{ originalEditingAzureVmSize }}</p>
            </div>
            <div>
              <label for="editAzureVmAdminPassword" class="block text-sm font-medium text-gray-700">New Admin Password (optional)</label>
              <input type="password" id="editAzureVmAdminPassword" v-model="editingAzureVm.admin_password" placeholder="Leave blank to keep current" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <p class="text-sm text-gray-600">Note: Changing VM size may require the VM to be stopped/restarted by Azure.</p>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeEditAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
              <button type="submit" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                <span v-if="isProcessingAzureVm">Saving...</span>
                <span v-else>Save Changes</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Azure VM Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteAzureVmModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto w-full h-full"> 
        <div
          class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white"> 
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">Delete Azure VM</h3>
          <div class="mt-2 px-7 py-3">
            <p class="text-sm text-gray-600">
              Are you sure you want to delete Azure VM <strong class="text-gray-800">{{ azureVmToDelete?.name }}</strong>? This action will attempt to deprovision it.
            </p>
            <div v-if="azureVmModalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ azureVmModalError.message || 'Could not process request.' }}</p>
                 <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                  Server: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
                </p>
              </div>
          </div>
          <div class="items-center px-4 py-3 space-x-4 flex justify-end">
            <button type="button" @click="closeDeleteAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
            <button @click="submitDeleteAzureVm" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
              <span v-if="isProcessingAzureVm">Deleting...</span>
              <span v-else>Delete VM</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, reactive } from 'vue';
import apiService from '@/services/api';

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  canManageAzureVms: {
    type: Boolean,
    required: true
  }
});

// Predefined options for Azure
const azureRegions = ref([
  'eastus', 'eastus2', 'westus', 'westus2', 'westus3',
  'centralus', 'northcentralus', 'southcentralus',
  'northeurope', 'westeurope', 'uksouth', 'ukwest',
  'japaneast', 'japanwest', 'australiaeast', 'australiasoutheast',
  'canadacentral', 'canadaeast'
]);

const azureVmSizes = ref([
  'Standard_B1s', 'Standard_B1ms', 'Standard_B2s', 'Standard_B2ms',
  'Standard_DS1_v2', 'Standard_DS2_v2', 'Standard_DS3_v2',
  'Standard_F1s', 'Standard_F2s_v2', 'Standard_F4s_v2',
  'Standard_E2s_v3', 'Standard_E4s_v3'
  // Add more common types as needed
]);

// --- Azure VM State ---
const azureVms = ref([]);
const isLoadingAzureVms = ref(false);
const azureVmsError = ref(null);

const azureVmModalError = ref(null); // Shared error display for Azure VM modals
const isProcessingAzureVm = ref(false); // Shared processing state for Azure VM modals

// --- Add Azure VM Modal State ---
const showAddAzureVmModal = ref(false);
const initialNewAzureVmState = () => ({
  name: '',
  region: azureRegions.value[0] || '', // Default to the first region
  vm_size: azureVmSizes.value[0] || '', // Default to the first VM size
  image_reference: {
    publisher: 'Canonical',
    offer: '0001-com-ubuntu-server-jammy',
    sku: '22_04-lts-gen2',
    version: 'latest'
  },
  admin_username: 'azureuser',
  admin_password: '',
  vnet_address_prefix: '', // Default will be handled by backend if empty
  subnet_prefix: '',       // Default will be handled by backend if empty
  public_ip_allocation_method: 'Dynamic'
});
const newAzureVm = reactive(initialNewAzureVmState());

// --- Edit Azure VM Modal State ---
const showEditAzureVmModal = ref(false);
const editingAzureVm = ref(null);
const originalEditingAzureVmSize = ref('');

// --- Delete Azure VM Modal State ---
const showDeleteAzureVmModal = ref(false);
const azureVmToDelete = ref(null);

// --- Action State (Start/Stop) ---
const isProcessingActionAzureVmId = ref(null); // Stores the name of the VM being acted upon
const azureVmActionInProgress = ref(''); // e.g., 'starting', 'stopping'
// const azureVmActionError = ref(null); // For errors specific to start/stop actions (can use azureVmModalError if preferred)


async function fetchAzureVms() {
  if (!props.projectId) return;
  isLoadingAzureVms.value = true;
  azureVmsError.value = null;
  try {
    const response = await apiService.get(`/resources/azure/vm/${props.projectId}`);
    azureVms.value = response.data;
  } catch (err) {
    console.error('Failed to fetch Azure VMs:', err);
    azureVmsError.value = err.response?.data || err;
  } finally {
    isLoadingAzureVms.value = false;
  }
}

async function handleRefreshAzureVms() {
  await fetchAzureVms();
}

// --- Add Azure VM Functions ---
function openAddAzureVmModal() {
  Object.assign(newAzureVm, initialNewAzureVmState()); // Reset form
  azureVmModalError.value = null;
  showAddAzureVmModal.value = true;
}

function closeAddAzureVmModal() {
  showAddAzureVmModal.value = false;
}

async function submitAddAzureVm() {
  // Basic validation (can be expanded)
  if (!newAzureVm.name || !newAzureVm.region || !newAzureVm.vm_size || !newAzureVm.admin_username || !newAzureVm.admin_password ||
      !newAzureVm.image_reference.publisher || !newAzureVm.image_reference.offer || !newAzureVm.image_reference.sku || !newAzureVm.image_reference.version) {
    azureVmModalError.value = { message: 'All required fields must be filled.' };
    return;
  }
  isProcessingAzureVm.value = true;
  azureVmModalError.value = null;

  // Filter out empty optional fields so backend defaults are used
  const payload = { ...newAzureVm };
  if (!payload.vnet_address_prefix) delete payload.vnet_address_prefix;
  if (!payload.subnet_prefix) delete payload.subnet_prefix;
  
  try {
    await apiService.post(`/resources/azure/vm/${props.projectId}`, payload);
    await fetchAzureVms();
    closeAddAzureVmModal();
  } catch (err) {
    console.error('Failed to add Azure VM:', err);
    azureVmModalError.value = err.response?.data || err;
  } finally {
    isProcessingAzureVm.value = false;
  }
}

// --- Edit Azure VM Functions ---
function openEditAzureVmModal(vm) {
  editingAzureVm.value = {
    name: vm.name, // name is not editable via API, but needed for URL
    // Ensure vm_size is a value present in our predefined list, or handle it
    vm_size: azureVmSizes.value.includes(vm.vm_size) ? vm.vm_size : (azureVmSizes.value[0] || ''),
    admin_password: '' 
  };
  originalEditingAzureVmSize.value = vm.vm_size || 'N/A';
  azureVmModalError.value = null;
  showEditAzureVmModal.value = true;
}

function closeEditAzureVmModal() {
  showEditAzureVmModal.value = false;
  editingAzureVm.value = null;
}

async function submitEditAzureVm() {
  if (!editingAzureVm.value || !editingAzureVm.value.vm_size) {
     azureVmModalError.value = { message: 'VM Size is required.' };
     return;
  }
  isProcessingAzureVm.value = true;
  azureVmModalError.value = null;
  
  const payload = {
    vm_size: editingAzureVm.value.vm_size
  };
  if (editingAzureVm.value.admin_password) { // Only include password if user entered one
    payload.admin_password = editingAzureVm.value.admin_password;
  }

  try {
    await apiService.patch(`/resources/azure/vm/${props.projectId}/${editingAzureVm.value.name}`, payload);
    await fetchAzureVms();
    closeEditAzureVmModal();
  } catch (err) {
    console.error(`Failed to update Azure VM ${editingAzureVm.value.name}:`, err);
    azureVmModalError.value = err.response?.data || err;
  } finally {
    isProcessingAzureVm.value = false;
  }
}

// --- Delete Azure VM Functions ---
function openDeleteAzureVmModal(vm) {
  console.log('openDeleteAzureVmModal called with vm:', vm); // DEBUG LINE
  azureVmToDelete.value = { ...vm };
  azureVmModalError.value = null;
  showDeleteAzureVmModal.value = true;
  console.log('showDeleteAzureVmModal value after setting true:', showDeleteAzureVmModal.value); // DEBUG LINE
}

function closeDeleteAzureVmModal() {
  showDeleteAzureVmModal.value = false;
  azureVmToDelete.value = null;
}

async function submitDeleteAzureVm() {
  if (!azureVmToDelete.value) return;
  isProcessingAzureVm.value = true;
  azureVmModalError.value = null;
  try {
    await apiService.delete(`/resources/azure/vm/${props.projectId}/${azureVmToDelete.value.name}`);
    await fetchAzureVms();
    closeDeleteAzureVmModal();
  } catch (err) {
    console.error('Failed to delete Azure VM:', err);
    azureVmModalError.value = err.response?.data || err;
  } finally {
    isProcessingAzureVm.value = false;
  }
}

// --- Azure VM Action Functions (Start/Stop/Delete/Edit Conditions) ---
// These are based on Azure VM states. You might need to adjust based on the exact string values of ResourceState enum.
// Common states: Succeeded, Failed, Canceled, Creating, Updating, Deleting, Starting, Stopping, Stopped, Deallocated, Terminated
function canViewDashboard(vm) {
  const status = vm.status ? vm.status.toLowerCase() : '';
  return !!vm.dashboard_url && 
         !status.includes('deleting') && 
         !status.includes('creating') &&
         !status.includes('terminated');
}

function canEditVm(vm) {
  const status = vm.status ? vm.status.toLowerCase() : '';
  return !status.includes('deleting') && 
         !status.includes('creating') &&
         !status.includes('terminated');
}

function canStartVm(vm) {
  const status = vm.status ? vm.status.toLowerCase() : '';
  // A terminated VM cannot be started. Only stopped or deallocated ones.
  return (status === 'stopped' || status === 'deallocated') && !status.includes('terminated');
}

function canStopVm(vm) { // Stop usually means deallocate for cost savings
  const status = vm.status ? vm.status.toLowerCase() : '';
  // A terminated VM cannot be stopped.
  return (status === 'running' || status === 'starting') && !status.includes('terminated');
}

function canDeleteVm(vm) {
  const status = vm.status ? vm.status.toLowerCase() : '';
  // If a VM is already terminated, deleting it again might be redundant or not allowed.
  // If 'deleting' is a transient state before 'terminated', this is fine.
  return !status.includes('deleting') && 
         !status.includes('creating') &&
         !status.includes('terminated');
}

// --- Start/Stop Actions ---
async function startAzureVm(vm) {
  if (!vm || !vm.name) return;
  isProcessingActionAzureVmId.value = vm.name;
  azureVmActionInProgress.value = 'starting';
  azureVmModalError.value = null; 
  try {
    await apiService.post(`/resources/azure/vm/${props.projectId}/${vm.name}/start`);
    await fetchAzureVms(); // Or update single item if API returns updated VM
  } catch (err) {
    console.error(`Failed to start Azure VM ${vm.name}:`, err);
    azureVmModalError.value = err.response?.data || err; // Show error in a general modal error spot or a dedicated one
  } finally {
    isProcessingActionAzureVmId.value = null;
    azureVmActionInProgress.value = '';
  }
}

async function stopAzureVm(vm) {
  if (!vm || !vm.name) return;
  isProcessingActionAzureVmId.value = vm.name;
  azureVmActionInProgress.value = 'stopping';
  azureVmModalError.value = null;
  try {
    await apiService.post(`/resources/azure/vm/${props.projectId}/${vm.name}/stop`);
    await fetchAzureVms();
  } catch (err) {
    console.error(`Failed to stop Azure VM ${vm.name}:`, err);
    azureVmModalError.value = err.response?.data || err;
  } finally {
    isProcessingActionAzureVmId.value = null;
    azureVmActionInProgress.value = '';
  }
}

function getStatusClass(status) {
  status = status ? status.toLowerCase() : '';
  // Adjust based on your ResourceState enum values and desired colors
  if (status.includes('running') || status.includes('succeeded')) { // 'Succeeded' can be a final state for some operations
    return 'bg-green-100 text-green-800';
  } else if (status.includes('pending') || status.includes('provisioning') || status.includes('creating') || status.includes('starting') || status.includes('stopping') || status.includes('updating')) {
    return 'bg-yellow-100 text-yellow-800';
  } else if (status.includes('stopped') || status.includes('deallocated') || status.includes('terminated')) { // 'VM deallocated' is common for stopped Azure VMs
    return 'bg-gray-100 text-gray-800';
  } else if (status.includes('error') || status.includes('failed') || status.includes('canceled')) {
    return 'bg-red-100 text-red-800';
  }
  return 'bg-blue-100 text-blue-800'; // Default for unknown or other transient states
}

function openGrafanaDashboard(vm) {
  const url = vm.dashboard_url;
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  } else {
    console.warn('Grafana dashboard URL not found for this Azure VM:', vm.name);
    alert('Dashboard URL is not available for this VM.');
  }
}

onMounted(() => {
  if (props.projectId) {
    fetchAzureVms();
  }
});

watch(() => props.projectId, (newProjectId) => {
  if (newProjectId) {
    fetchAzureVms();
  } else {
    azureVms.value = [];
  }
});

</script>

<style scoped>
/* Styles can be kept for non-Tailwind specific things or removed if not needed */
</style>