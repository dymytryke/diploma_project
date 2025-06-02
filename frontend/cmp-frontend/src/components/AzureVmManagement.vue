<template>
  <div class="mt-10 pt-6 border-t">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-semibold text-gray-700">{{ $t('azureVmManagement.title') }}</h2>
      <div class="space-x-2">
        <button
          @click="handleRefreshAzureVms"
          :disabled="isLoadingAzureVms"
          class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-300"
        >
          <span v-if="isLoadingAzureVms && !isProcessingActionAzureVmId">{{ $t('azureVmManagement.refreshingButton') }}</span>
          <span v-else>{{ $t('common.refreshList') }}</span>
        </button>
        <button
          v-if="canManageAzureVms"
          @click="openAddAzureVmModal"
          class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          {{ $t('azureVmManagement.addVmButton') }}
        </button>
      </div>
    </div>

    <!-- Loading Azure VMs -->
    <div v-if="isLoadingAzureVms" class="text-center text-gray-500">
      <p>{{ $t('azureVmManagement.loadingVms') }}</p>
    </div>
    <!-- Error Loading Azure VMs -->
    <div v-else-if="azureVmsError" class="text-red-500 p-3 bg-red-100 rounded">
      <p>{{ $t('azureVmManagement.errorLoadingVms') }}: {{ azureVmsError.message || $t('common.unknownError') }}</p>
      <p v-if="azureVmsError.response && azureVmsError.response.data && azureVmsError.response.data.detail">
        {{ $t('common.serverErrorPrefix') }}: {{ typeof azureVmsError.response.data.detail === 'string' ? azureVmsError.response.data.detail : JSON.stringify(azureVmsError.response.data.detail) }}
      </p>
    </div>
    <!-- Azure VMs Table -->
    <div v-else-if="azureVms.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('azureVmManagement.table.nameCmp') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('azureVmManagement.table.region') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('azureVmManagement.table.vmSize') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.status') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('azureVmManagement.table.publicIp') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('azureVmManagement.table.resourceGroup') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="vm in azureVms" :key="vm.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.name }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.region }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.vm_size || $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <span :class="getStatusClass(vm.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                {{ vm.status }}
              </span>
              <span v-if="isProcessingActionAzureVmId === vm.name" class="ml-2 text-xs text-gray-500">({{ $t(`azureVmManagement.actions.${azureVmActionInProgress}`) }})</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.public_ip || $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ vm.resource_group || $t('common.notAvailable') }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="canViewDashboard(vm) && canManageAzureVms"
                @click="openGrafanaDashboard(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-blue-600 hover:text-blue-900 disabled:text-gray-400"
                :title="$t('azureVmManagement.actions.viewDashboardTitle')"
              >
                {{ $t('azureVmManagement.actions.dashboard') }}
              </button>
              <button
                v-if="canEditVm(vm) && canManageAzureVms"
                @click="openEditAzureVmModal(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-yellow-600 hover:text-yellow-900 disabled:text-gray-400"
              >
                {{ $t('common.edit') }}
              </button>
              <button
                v-if="canStartVm(vm) && canManageAzureVms"
                @click="startAzureVm(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-green-600 hover:text-green-900 disabled:text-gray-400"
              >
                {{ $t('azureVmManagement.actions.start') }}
              </button>
              <button
                v-if="canStopVm(vm) && canManageAzureVms"
                @click="stopAzureVm(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
              >
                {{ $t('azureVmManagement.actions.stop') }}
              </button>
              <button
                v-if="canDeleteVm(vm) && canManageAzureVms"
                @click="openDeleteAzureVmModal(vm)"
                :disabled="isProcessingActionAzureVmId === vm.name"
                class="text-red-600 hover:text-red-900 disabled:text-gray-400"
              >
                {{ $t('common.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-gray-500 text-center py-4">
      <p>{{ $t('azureVmManagement.noVmsFound') }}</p>
    </div>

    <!-- Add Azure VM Modal -->
    <Teleport to="body">
      <div v-if="showAddAzureVmModal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto w-full h-full">
        <div
          class="relative mx-auto p-5 border w-full max-w-xl shadow-lg rounded-md bg-white"> 
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center mb-4">{{ $t('azureVmManagement.addModal.title') }}</h3>
          <form @submit.prevent="submitAddAzureVm" class="space-y-4 max-h-[80vh] overflow-y-auto px-2">
            <div v-if="azureVmModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ azureVmModalError.message || $t('common.couldNotProcessRequest') }}</p>
              <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                {{ $t('common.serverErrorPrefix') }}: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
              </p>
            </div>

            <div>
              <label for="azureVmName" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.addModal.nameLabel') }}</label>
              <input type="text" id="azureVmName" v-model="newAzureVm.name" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <div>
              <label for="azureVmRegion" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.addModal.regionLabel') }}</label>
              <select id="azureVmRegion" v-model="newAzureVm.region" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="region in azureRegions" :key="region" :value="region">{{ region }}</option>
              </select>
            </div>
            <div>
              <label for="azureVmSize" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.addModal.vmSizeLabel') }}</label>
              <select id="azureVmSize" v-model="newAzureVm.vm_size" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="size in azureVmSizes" :key="size" :value="size">{{ size }}</option>
              </select>
            </div>
            <div>
              <label for="azureVmAdminUsername" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.addModal.adminUsernameLabel') }}</label>
              <input type="text" id="azureVmAdminUsername" v-model="newAzureVm.admin_username" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <div>
              <label for="azureVmAdminPassword" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.addModal.adminPasswordLabel') }}</label>
              <input type="password" id="azureVmAdminPassword" v-model="newAzureVm.admin_password" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>

            <fieldset class="border p-4 rounded-md">
              <legend class="text-sm font-medium text-gray-700 px-1">{{ $t('azureVmManagement.addModal.imageReferenceLegend') }}</legend>
              <div class="space-y-3">
                <div>
                  <label for="azureVmImgPublisher" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.imagePublisherLabel') }}</label>
                  <input type="text" id="azureVmImgPublisher" v-model="newAzureVm.image_reference.publisher" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgOffer" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.imageOfferLabel') }}</label>
                  <input type="text" id="azureVmImgOffer" v-model="newAzureVm.image_reference.offer" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgSku" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.imageSkuLabel') }}</label>
                  <input type="text" id="azureVmImgSku" v-model="newAzureVm.image_reference.sku" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
                <div>
                  <label for="azureVmImgVersion" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.imageVersionLabel') }}</label>
                  <input type="text" id="azureVmImgVersion" v-model="newAzureVm.image_reference.version" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                </div>
              </div>
            </fieldset>
            
            <details class="border p-2 rounded-md">
                <summary class="text-sm font-medium text-gray-700 cursor-pointer">{{ $t('azureVmManagement.addModal.advancedNetworkOptions') }}</summary>
                <div class="mt-2 space-y-3 p-2">
                    <div>
                        <label for="azureVmVnetPrefix" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.vnetPrefixLabel') }}</label>
                        <input type="text" id="azureVmVnetPrefix" v-model="newAzureVm.vnet_address_prefix" :placeholder="$t('azureVmManagement.addModal.vnetPrefixPlaceholder')" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                    </div>
                    <div>
                        <label for="azureVmSubnetPrefix" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.subnetPrefixLabel') }}</label>
                        <input type="text" id="azureVmSubnetPrefix" v-model="newAzureVm.subnet_prefix" :placeholder="$t('azureVmManagement.addModal.subnetPrefixPlaceholder')" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                    </div>
                    <div>
                        <label for="azureVmPublicIpAlloc" class="block text-xs font-medium text-gray-600">{{ $t('azureVmManagement.addModal.publicIpAllocationLabel') }}</label>
                        <select id="azureVmPublicIpAlloc" v-model="newAzureVm.public_ip_allocation_method" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs">
                            <option value="Dynamic">{{ $t('azureVmManagement.addModal.ipAllocationDynamic') }}</option>
                            <option value="Static">{{ $t('azureVmManagement.addModal.ipAllocationStatic') }}</option>
                        </select>
                    </div>
                </div>
            </details>

            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeAddAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
              <button type="submit" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:bg-purple-300">
                <span v-if="isProcessingAzureVm">{{ $t('azureVmManagement.addModal.addingButton') }}</span>
                <span v-else>{{ $t('azureVmManagement.addModal.addVmButton') }}</span>
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
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center mb-4">{{ $t('azureVmManagement.editModal.title', { name: editingAzureVm?.name }) }}</h3>
          <form @submit.prevent="submitEditAzureVm" class="space-y-4">
            <div v-if="azureVmModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
              <p>{{ azureVmModalError.message || $t('common.couldNotProcessRequest') }}</p>
              <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                {{ $t('common.serverErrorPrefix') }}: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
              </p>
            </div>
            <div>
              <label for="editAzureVmSize" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.editModal.newVmSizeLabel') }}</label>
              <select id="editAzureVmSize" v-model="editingAzureVm.vm_size" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
                <option v-for="size in azureVmSizes" :key="size" :value="size">{{ size }}</option>
              </select>
              <p class="mt-1 text-xs text-gray-500">{{ $t('azureVmManagement.editModal.currentSizeLabel') }}: {{ originalEditingAzureVmSize }}</p>
            </div>
            <div>
              <label for="editAzureVmAdminPassword" class="block text-sm font-medium text-gray-700">{{ $t('azureVmManagement.editModal.newAdminPasswordLabel') }}</label>
              <input type="password" id="editAzureVmAdminPassword" v-model="editingAzureVm.admin_password" :placeholder="$t('azureVmManagement.editModal.passwordPlaceholder')" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm">
            </div>
            <p class="text-sm text-gray-600">{{ $t('azureVmManagement.editModal.sizeChangeNote') }}</p>
            <div class="flex justify-end space-x-3 pt-4">
              <button type="button" @click="closeEditAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
              <button type="submit" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                <span v-if="isProcessingAzureVm">{{ $t('common.saving') }}</span>
                <span v-else>{{ $t('common.saveChanges') }}</span>
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
          <h3 class="text-lg font-medium leading-6 text-gray-900 text-center">{{ $t('azureVmManagement.deleteModal.title') }}</h3>
          <div class="mt-2 px-7 py-3">
            <p class="text-sm text-gray-600" v-html="$t('azureVmManagement.deleteModal.confirmationText', { name: azureVmToDelete?.name })"></p>
            <div v-if="azureVmModalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ azureVmModalError.message || $t('common.couldNotProcessRequest') }}</p>
                 <p v-if="azureVmModalError.response && azureVmModalError.response.data && azureVmModalError.response.data.detail">
                  {{ $t('common.serverErrorPrefix') }}: {{ typeof azureVmModalError.response.data.detail === 'string' ? azureVmModalError.response.data.detail : JSON.stringify(azureVmModalError.response.data.detail) }}
                </p>
              </div>
          </div>
          <div class="items-center px-4 py-3 space-x-4 flex justify-end">
            <button type="button" @click="closeDeleteAzureVmModal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">{{ $t('common.cancel') }}</button>
            <button @click="submitDeleteAzureVm" :disabled="isProcessingAzureVm" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
              <span v-if="isProcessingAzureVm">{{ $t('common.deleting') }}</span>
              <span v-else>{{ $t('azureVmManagement.deleteModal.deleteButton') }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Integrated Dashboard Modal for Azure VM -->
    <Teleport to="body">
      <div v-if="showDashboardModalAzure"
           class="fixed inset-0 bg-gray-900 bg-opacity-75 z-50 flex items-center justify-center p-4">
        <div class="relative bg-white rounded-lg shadow-xl w-full h-[90vh] max-w-6xl flex flex-col">
          <div class="flex justify-between items-center p-4 border-b">
            <h3 class="text-lg font-medium text-gray-900">{{ $t('azureVmManagement.dashboardModal.title') }}</h3>
            <button @click="closeDashboardModalAzure" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
          <div class="flex-grow p-1 overflow-hidden">
            <iframe
              v-if="dashboardModalUrlAzure"
              :src="dashboardModalUrlAzure"
              class="w-full h-full border-0"
              allowfullscreen
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            ></iframe>
            <div v-else class="flex items-center justify-center h-full text-gray-500">
              {{ $t('azureVmManagement.dashboardModal.loadingDashboard') }}
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, watch, reactive } from 'vue';
import apiService from '@/services/api';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
  region: azureRegions.value[0] || '', 
  vm_size: azureVmSizes.value[0] || '', 
  image_reference: {
    publisher: 'Canonical',
    offer: '0001-com-ubuntu-server-jammy',
    sku: '22_04-lts-gen2',
    version: 'latest'
  },
  admin_username: 'azureuser',
  admin_password: '',
  vnet_address_prefix: '', 
  subnet_prefix: '',       
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
const isProcessingActionAzureVmId = ref(null); 
const azureVmActionInProgress = ref(''); 

// --- Integrated Dashboard Modal State ---
const showDashboardModalAzure = ref(false);
const dashboardModalUrlAzure = ref('');


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
  Object.assign(newAzureVm, initialNewAzureVmState()); 
  azureVmModalError.value = null;
  showAddAzureVmModal.value = true;
}

function closeAddAzureVmModal() {
  showAddAzureVmModal.value = false;
}

async function submitAddAzureVm() {
  if (!newAzureVm.name || !newAzureVm.region || !newAzureVm.vm_size || !newAzureVm.admin_username || !newAzureVm.admin_password ||
      !newAzureVm.image_reference.publisher || !newAzureVm.image_reference.offer || !newAzureVm.image_reference.sku || !newAzureVm.image_reference.version) {
    azureVmModalError.value = { message: t('azureVmManagement.addModal.allFieldsRequiredError') };
    return;
  }
  isProcessingAzureVm.value = true;
  azureVmModalError.value = null;

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
    name: vm.name, 
    vm_size: azureVmSizes.value.includes(vm.vm_size) ? vm.vm_size : (azureVmSizes.value[0] || ''),
    admin_password: '' 
  };
  originalEditingAzureVmSize.value = vm.vm_size || t('common.notAvailable');
  azureVmModalError.value = null;
  showEditAzureVmModal.value = true;
}

function closeEditAzureVmModal() {
  showEditAzureVmModal.value = false;
  editingAzureVm.value = null;
}

async function submitEditAzureVm() {
  if (!editingAzureVm.value || !editingAzureVm.value.vm_size) {
     azureVmModalError.value = { message: t('azureVmManagement.editModal.vmSizeRequiredError') };
     return;
  }
  isProcessingAzureVm.value = true;
  azureVmModalError.value = null;
  
  const payload = {
    vm_size: editingAzureVm.value.vm_size
  };
  if (editingAzureVm.value.admin_password) { 
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
  azureVmToDelete.value = { ...vm };
  azureVmModalError.value = null;
  showDeleteAzureVmModal.value = true;
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
  return (status === 'stopped' || status === 'deallocated') && !status.includes('terminated');
}

function canStopVm(vm) { 
  const status = vm.status ? vm.status.toLowerCase() : '';
  return (status === 'running' || status === 'starting') && !status.includes('terminated');
}

function canDeleteVm(vm) {
  const status = vm.status ? vm.status.toLowerCase() : '';
  return !status.includes('deleting') && 
         !status.includes('creating') &&
         !status.includes('terminated');
}

async function startAzureVm(vm) {
  if (!vm || !vm.name) return;
  isProcessingActionAzureVmId.value = vm.name;
  azureVmActionInProgress.value = 'starting';
  azureVmModalError.value = null; 
  try {
    await apiService.post(`/resources/azure/vm/${props.projectId}/${vm.name}/start`);
    await fetchAzureVms(); 
  } catch (err) {
    console.error(`Failed to start Azure VM ${vm.name}:`, err);
    azureVmModalError.value = err.response?.data || err; 
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
  if (status.includes('running') || status.includes('succeeded')) { 
    return 'bg-green-100 text-green-800';
  } else if (status.includes('pending') || status.includes('provisioning') || status.includes('creating') || status.includes('starting') || status.includes('stopping') || status.includes('updating')) {
    return 'bg-yellow-100 text-yellow-800';
  } else if (status.includes('stopped') || status.includes('deallocated') || status.includes('terminated')) { 
    return 'bg-gray-100 text-gray-800';
  } else if (status.includes('error') || status.includes('failed') || status.includes('canceled')) {
    return 'bg-red-100 text-red-800';
  }
  return 'bg-blue-100 text-blue-800'; 
}

function openGrafanaDashboard(vm) { 
  const url = vm.dashboard_url;
  if (url) {
    dashboardModalUrlAzure.value = url;
    showDashboardModalAzure.value = true;
  } else {
    console.warn('Grafana dashboard URL not found for this Azure VM:', vm.name);
    azureVmModalError.value = { message: t('azureVmManagement.dashboardModal.urlNotAvailableError', { name: vm.name }) };
  }
}

function closeDashboardModalAzure() {
  showDashboardModalAzure.value = false;
  dashboardModalUrlAzure.value = ''; 
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