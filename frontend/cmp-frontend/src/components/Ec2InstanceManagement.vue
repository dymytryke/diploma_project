<template>
  <div class="mt-10 pt-6 border-t">
    <!-- ... existing code for title and buttons ... -->
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-semibold text-gray-700">AWS EC2 Instances</h2>
      <div class="space-x-2">
        <button
          @click="handleRefreshEc2Instances"
          :disabled="isLoadingEc2Instances"
          class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-300"
        >
          <span v-if="isLoadingEc2Instances && !isProcessingActionEc2InstanceId">Refreshing...</span>
          <span v-else>Refresh List</span>
        </button>
        <button
          v-if="canManageEc2"
          @click="openAddEc2Modal"
          class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          Add EC2 Instance
        </button>
      </div>
    </div>

    <!-- Loading EC2 Instances -->
    <div v-if="isLoadingEc2Instances" class="text-center text-gray-500">
      <p>Loading EC2 instances...</p>
    </div>
    <!-- Error Loading EC2 Instances -->
    <div v-else-if="ec2InstancesError" class="text-red-500 p-3 bg-red-100 rounded">
      <p>Error loading EC2 instances: {{ ec2InstancesError.message || 'Unknown error' }}</p>
      <p v-if="ec2InstancesError.response && ec2InstancesError.response.data && ec2InstancesError.response.data.detail">
        Server: {{ typeof ec2InstancesError.response.data.detail === 'string' ? ec2InstancesError.response.data.detail : JSON.stringify(ec2InstancesError.response.data.detail) }}
      </p>
    </div>
    <!-- EC2 Instances Table -->
    <div v-else-if="ec2Instances.length > 0" class="overflow-x-auto bg-white shadow-md rounded-lg">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name (CMP)</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AWS ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Region</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AMI</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Public IP</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Launch Time</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="instance in ec2Instances" :key="instance.name">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.name }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.aws_id || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.region }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.instance_type }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.ami || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <span :class="getStatusClass(instance.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                {{ instance.status }}
              </span>
              <span v-if="isProcessingActionEc2InstanceId === instance.name" class="ml-2 text-xs text-gray-500">({{ ec2ActionInProgress }})</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.public_ip || 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{{ instance.launch_time ? new Date(instance.launch_time).toLocaleString() : 'N/A' }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
              <button
                v-if="canViewDashboard(instance) && canManageEc2"
                @click="openIntegratedDashboardEc2(instance)"
                :disabled="isProcessingActionEc2InstanceId === instance.name"
                class="text-blue-600 hover:text-blue-900 disabled:text-gray-400"
                title="View Integrated Dashboard"
              >
                Dashboard
              </button>
              <button
                v-if="canEditInstance(instance) && canManageEc2"
                @click="openEditEc2Modal(instance)"
                :disabled="isProcessingActionEc2InstanceId === instance.name"
                class="text-yellow-600 hover:text-yellow-900 disabled:text-gray-400"
              >
                Edit
              </button>
              <button
                v-if="canStartInstance(instance) && canManageEc2"
                @click="startEc2Instance(instance)"
                :disabled="isProcessingActionEc2InstanceId === instance.name"
                class="text-green-600 hover:text-green-900 disabled:text-gray-400"
              >
                Start
              </button>
              <button
                v-if="canStopInstance(instance) && canManageEc2"
                @click="stopEc2Instance(instance)"
                :disabled="isProcessingActionEc2InstanceId === instance.name"
                class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
              >
                Stop
              </button>
              <button
                v-if="canDeleteInstance(instance) && canManageEc2"
                @click="openDeleteEc2Modal(instance)"
                :disabled="isProcessingActionEc2InstanceId === instance.name"
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
      <p>No EC2 instances found for this project.</p>
    </div>

    <!-- Add EC2 Instance Modal -->
    <Teleport to="body">
      <div v-if="showAddEc2Modal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto"> 
        <div class="relative mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Add New EC2 Instance</h3>
            <form @submit.prevent="submitAddEc2Instance" class="mt-2 px-7 py-3 text-left">
              <div v-if="ec2ModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ ec2ModalError.message || 'Could not process request.' }}</p>
                 <p v-if="ec2ModalError.response && ec2ModalError.response.data && ec2ModalError.response.data.detail">
                  Server: {{ typeof ec2ModalError.response.data.detail === 'string' ? ec2ModalError.response.data.detail : JSON.stringify(ec2ModalError.response.data.detail) }}
                </p>
              </div>

              <div class="mb-4">
                <label for="ec2Name" class="block text-sm font-medium text-gray-700">Name (CMP Internal)</label>
                <input type="text" id="ec2Name" v-model="newEc2Instance.name" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
              </div>
              <div class="mb-4">
                <label for="ec2Region" class="block text-sm font-medium text-gray-700">Region</label>
                <select id="ec2Region" v-model="newEc2Instance.region" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                  <option v-for="region in ec2Regions" :key="region" :value="region">{{ region }}</option>
                </select>
              </div>
              <div class="mb-4">
                <label for="ec2InstanceType" class="block text-sm font-medium text-gray-700">Instance Type</label>
                <select id="ec2InstanceType" v-model="newEc2Instance.instance_type" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                  <option v-for="type in ec2InstanceTypes" :key="type" :value="type">{{ type }}</option>
                </select>
              </div>
              <div class="mb-4">
                <label for="ec2Ami" class="block text-sm font-medium text-gray-700">AMI ID (e.g., ami-xxxxxxxxxxxxxxxxx)</label>
                <input type="text" id="ec2Ami" v-model="newEc2Instance.ami" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                <p class="mt-1 text-xs text-gray-500">Ensure AMI is compatible with selected region.</p>
              </div>

              <div class="items-center px-4 py-3 space-x-4 flex justify-end">
                <button type="button" @click="closeAddEc2Modal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
                <button type="submit" :disabled="isProcessingEc2" class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-blue-300">
                  <span v-if="isProcessingEc2">Adding...</span>
                  <span v-else>Add Instance</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit EC2 Instance Modal -->
    <Teleport to="body">
      <div v-if="showEditEc2Modal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto">
        <div class="relative mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Edit EC2 Instance: {{ editingEc2Instance?.name }}</h3>
            <form @submit.prevent="submitEditEc2Instance" class="mt-2 px-7 py-3 text-left">
              <div v-if="ec2ModalError" class="mb-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ ec2ModalError.message || 'Could not process request.' }}</p>
                 <p v-if="ec2ModalError.response && ec2ModalError.response.data && ec2ModalError.response.data.detail">
                  Server: {{ typeof ec2ModalError.response.data.detail === 'string' ? ec2ModalError.response.data.detail : JSON.stringify(ec2ModalError.response.data.detail) }}
                </p>
              </div>

              <div class="mb-4">
                <label for="editEc2InstanceType" class="block text-sm font-medium text-gray-700">New Instance Type</label>
                <select id="editEc2InstanceType" v-model="editingEc2Instance.instance_type" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                  <option v-for="type in ec2InstanceTypes" :key="type" :value="type">{{ type }}</option>
                </select>
                <p class="mt-1 text-xs text-gray-500">Current type: {{ originalEditingEc2InstanceType }}</p>
              </div>
              <p class="text-sm text-gray-600 mb-4">Note: Changing instance type typically requires the instance to be stopped. The API will attempt the change.</p>


              <div class="items-center px-4 py-3 space-x-4 flex justify-end">
                <button type="button" @click="closeEditEc2Modal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
                <button type="submit" :disabled="isProcessingEc2" class="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:bg-yellow-300">
                  <span v-if="isProcessingEc2">Saving...</span>
                  <span v-else>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete EC2 Instance Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteEc2Modal"
           class="fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
          <div class="mt-3 text-center">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Delete EC2 Instance</h3>
            <div class="mt-2 px-7 py-3">
              <p class="text-sm text-gray-600">
                Are you sure you want to delete EC2 instance <strong class="text-gray-800">{{ ec2ToDelete?.name }}</strong> (AWS ID: {{ ec2ToDelete?.aws_id || 'N/A' }})? This action will attempt to deprovision it.
              </p>
              <div v-if="ec2ModalError" class="mt-4 p-3 bg-red-100 text-red-700 rounded text-sm">
                <p>{{ ec2ModalError.message || 'Could not process request.' }}</p>
                 <p v-if="ec2ModalError.response && ec2ModalError.response.data && ec2ModalError.response.data.detail">
                  Server: {{ typeof ec2ModalError.response.data.detail === 'string' ? ec2ModalError.response.data.detail : JSON.stringify(ec2ModalError.response.data.detail) }}
                </p>
              </div>
            </div>
            <div class="items-center px-4 py-3 space-x-4 flex justify-end">
              <button type="button" @click="closeDeleteEc2Modal" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Cancel</button>
              <button @click="submitDeleteEc2Instance" :disabled="isProcessingEc2" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-red-400">
                <span v-if="isProcessingEc2">Deleting...</span>
                <span v-else>Delete Instance</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Integrated Dashboard Modal for EC2 -->
    <Teleport to="body">
      <div v-if="showDashboardModalEc2"
           class="fixed inset-0 bg-gray-900 bg-opacity-75 z-50 flex items-center justify-center p-4">
        <div class="relative bg-white rounded-lg shadow-xl w-full h-[90vh] max-w-6xl flex flex-col">
          <div class="flex justify-between items-center p-4 border-b">
            <h3 class="text-lg font-medium text-gray-900">EC2 Instance Dashboard</h3>
            <button @click="closeDashboardModalEc2" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
          <div class="flex-grow p-1 overflow-hidden">
            <iframe
              v-if="dashboardModalUrlEc2"
              :src="dashboardModalUrlEc2"
              class="w-full h-full border-0"
              allowfullscreen
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups" 
            ></iframe>
            <div v-else class="flex items-center justify-center h-full text-gray-500">
              Loading dashboard...
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import apiService from '@/services/api';

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  canManageEc2: { // Combined permission prop
    type: Boolean,
    required: true
  }
});

// Predefined options for EC2
const ec2Regions = ref([
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'ca-central-1', 'eu-west-1', 'eu-central-1', 'eu-west-2',
  'eu-west-3', 'eu-north-1', 'ap-northeast-1', 'ap-northeast-2',
  'ap-southeast-1', 'ap-southeast-2', 'ap-south-1', 'sa-east-1'
]);

const ec2InstanceTypes = ref([
  't2.nano', 't2.micro', 't2.small', 't2.medium', 't2.large',
  't3.nano', 't3.micro', 't3.small', 't3.medium', 't3.large',
  'm5.large', 'm5.xlarge', 'c5.large', 'c5.xlarge', 'r5.large'
  // Add more common types as needed
]);

// --- EC2 Instance State ---
const ec2Instances = ref([]);
const isLoadingEc2Instances = ref(false);
const ec2InstancesError = ref(null);

const showAddEc2Modal = ref(false);
const newEc2Instance = ref({
  name: '',
  region: '',
  instance_type: '',
  ami: ''
});
const ec2ModalError = ref(null); // Shared error display for EC2 modals
const isProcessingEc2 = ref(false); // Shared processing state for EC2 modals

const showDeleteEc2Modal = ref(false);
const ec2ToDelete = ref(null);

const isProcessingActionEc2InstanceId = ref(null); // Stores the name of the EC2 instance being acted upon (start/stop)
const ec2ActionInProgress = ref(''); // e.g., 'starting', 'stopping'
const ec2ActionError = ref(null); // For errors specific to start/stop actions

const showEditEc2Modal = ref(false);
const editingEc2Instance = ref(null); // For the EC2 instance being edited
const originalEditingEc2InstanceType = ref(''); // To show the original type in the modal

// --- Integrated Dashboard Modal State ---
const showDashboardModalEc2 = ref(false);
const dashboardModalUrlEc2 = ref('');


async function fetchEc2Instances() {
  if (!props.projectId) return;
  isLoadingEc2Instances.value = true;
  ec2InstancesError.value = null;
  try {
    const response = await apiService.get(`/resources/aws/ec2/${props.projectId}`);
    ec2Instances.value = response.data;
  } catch (err) {
    console.error('Failed to fetch EC2 instances:', err);
    ec2InstancesError.value = err.response?.data || err;
  } finally {
    isLoadingEc2Instances.value = false;
  }
}

// New handler for the refresh button
async function handleRefreshEc2Instances() {
  await fetchEc2Instances();
}

// --- EC2 Instance Functions ---
function openAddEc2Modal() {
  newEc2Instance.value = { 
    name: '', 
    region: ec2Regions.value[0] || '', // Default to the first region
    instance_type: ec2InstanceTypes.value[0] || '', // Default to the first type
    ami: '' 
  };
  ec2ModalError.value = null;
  showAddEc2Modal.value = true;
}

function closeAddEc2Modal() {
  showAddEc2Modal.value = false;
}

async function submitAddEc2Instance() {
  if (!newEc2Instance.value.name || !newEc2Instance.value.region || !newEc2Instance.value.instance_type || !newEc2Instance.value.ami) {
    ec2ModalError.value = { message: 'All fields are required for EC2 instance.' };
    return;
  }
  isProcessingEc2.value = true;
  ec2ModalError.value = null;
  try {
    await apiService.post(`/resources/aws/ec2/${props.projectId}`, newEc2Instance.value);
    await fetchEc2Instances(); // Refresh list
    closeAddEc2Modal();
  } catch (err) {
    console.error('Failed to add EC2 instance:', err);
    ec2ModalError.value = err.response?.data || err;
  } finally {
    isProcessingEc2.value = false;
  }
}

function openDeleteEc2Modal(instance) {
  ec2ToDelete.value = { ...instance };
  ec2ModalError.value = null;
  showDeleteEc2Modal.value = true;
}

function closeDeleteEc2Modal() {
  showDeleteEc2Modal.value = false;
  ec2ToDelete.value = null;
}

async function submitDeleteEc2Instance() {
  if (!ec2ToDelete.value) return;
  isProcessingEc2.value = true;
  ec2ModalError.value = null;
  try {
    await apiService.delete(`/resources/aws/ec2/${props.projectId}/${ec2ToDelete.value.name}`);
    await fetchEc2Instances(); // Refresh list
    closeDeleteEc2Modal();
  } catch (err) {
    console.error('Failed to delete EC2 instance:', err);
    ec2ModalError.value = err.response?.data || err;
  } finally {
    isProcessingEc2.value = false;
  }
}

// --- Edit EC2 Instance Modal Functions ---
function openEditEc2Modal(instance) {
  editingEc2Instance.value = { 
    ...instance,
    // Ensure instance_type is a value present in our predefined list, or handle it
    instance_type: ec2InstanceTypes.value.includes(instance.instance_type) ? instance.instance_type : (ec2InstanceTypes.value[0] || '')
  };
  originalEditingEc2InstanceType.value = instance.instance_type;
  ec2ModalError.value = null;
  showEditEc2Modal.value = true;
}

function closeEditEc2Modal() {
  showEditEc2Modal.value = false;
  editingEc2Instance.value = null;
  originalEditingEc2InstanceType.value = '';
}

async function submitEditEc2Instance() {
  if (!editingEc2Instance.value || !editingEc2Instance.value.instance_type) {
    ec2ModalError.value = { message: 'New instance type is required.' };
    return;
  }
  isProcessingEc2.value = true;
  ec2ModalError.value = null;
  try {
    const payload = {
      instance_type: editingEc2Instance.value.instance_type
    };
    await apiService.patch(`/resources/aws/ec2/${props.projectId}/${editingEc2Instance.value.name}`, payload);
    await fetchEc2Instances(); // Refresh list
    closeEditEc2Modal();
  } catch (err) {
    console.error(`Failed to update EC2 instance ${editingEc2Instance.value.name}:`, err);
    ec2ModalError.value = err.response?.data || err;
  } finally {
    isProcessingEc2.value = false;
  }
}


// --- EC2 Instance Action Functions (Start/Stop/Delete/Edit Conditions) ---
function canViewDashboard(instance) {
  const status = instance.status ? instance.status.toLowerCase() : '';
  return !!instance.dashboard_url && status !== 'terminated' && status !== 'deprovisioning';
}

function canEditInstance(instance) {
  const status = instance.status ? instance.status.toLowerCase() : '';
  return status !== 'terminated' && status !== 'deprovisioning';
}

function canStartInstance(instance) {
  const status = instance.status ? instance.status.toLowerCase() : '';
  return status === 'stopped';
}

function canStopInstance(instance) {
  const status = instance.status ? instance.status.toLowerCase() : '';
  return status === 'running' || status === 'pending' || status === 'starting' || status === 'provisioning' || status === 'updating';
}

function canDeleteInstance(instance) {
  const status = instance.status ? instance.status.toLowerCase() : '';
  return status !== 'terminated' && status !== 'deprovisioning';
}


async function startEc2Instance(instance) {
  if (!instance || !instance.name) return;
  isProcessingActionEc2InstanceId.value = instance.name;
  ec2ActionInProgress.value = 'starting';
  ec2ActionError.value = null;
  ec2ModalError.value = null;
  try {
    await apiService.post(`/resources/aws/ec2/${props.projectId}/${instance.name}/start`);
    await fetchEc2Instances();
  } catch (err) {
    console.error(`Failed to start EC2 instance ${instance.name}:`, err);
    ec2ActionError.value = err.response?.data || err;
  } finally {
    isProcessingActionEc2InstanceId.value = null;
    ec2ActionInProgress.value = '';
  }
}

async function stopEc2Instance(instance) {
  if (!instance || !instance.name) return;
  isProcessingActionEc2InstanceId.value = instance.name;
  ec2ActionInProgress.value = 'stopping';
  ec2ActionError.value = null;
  ec2ModalError.value = null;
  try {
    await apiService.post(`/resources/aws/ec2/${props.projectId}/${instance.name}/stop`);
    await fetchEc2Instances();
  } catch (err) {
    console.error(`Failed to stop EC2 instance ${instance.name}:`, err);
    ec2ActionError.value = err.response?.data || err;
  } finally {
    isProcessingActionEc2InstanceId.value = null;
    ec2ActionInProgress.value = '';
  }
}

function getStatusClass(status) {
  status = status ? status.toLowerCase() : '';
  if (status.includes('running') || status.includes('ok') || status.includes('available')) {
    return 'bg-green-100 text-green-800';
  } else if (status.includes('pending') || status.includes('provisioning') || status.includes('starting') || status.includes('stopping') || status.includes('updating')) {
    return 'bg-yellow-100 text-yellow-800';
  } else if (status.includes('stopped') || status.includes('terminated')) {
    return 'bg-gray-100 text-gray-800';
  } else if (status.includes('error') || status.includes('failed')) {
    return 'bg-red-100 text-red-800';
  }
  return 'bg-blue-100 text-blue-800'; // Default for unknown statuses
}


// --- Grafana Dashboard ---
function openIntegratedDashboardEc2(instance) {
  const url = instance.dashboard_url;
  console.log('Attempting to open EC2 integrated Grafana dashboard. Instance:', instance, 'URL:', url);
  if (url) {
    dashboardModalUrlEc2.value = url;
    showDashboardModalEc2.value = true;
  } else {
    console.warn('Grafana dashboard URL not found for this EC2 instance:', instance.name);
    // Optionally, show a small notification or use ec2ModalError
    ec2ModalError.value = { message: `Dashboard URL is not available for instance ${instance.name}.` };
    // Consider adding a small, dismissible alert component for such messages if ec2ModalError is too intrusive
  }
}

function closeDashboardModalEc2() {
  showDashboardModalEc2.value = false;
  dashboardModalUrlEc2.value = ''; // Clear URL to ensure iframe reloads if opened again
}

onMounted(() => {
  if (props.projectId) {
    fetchEc2Instances();
  }
});

watch(() => props.projectId, (newProjectId) => {
  if (newProjectId) {
    fetchEc2Instances();
  } else {
    ec2Instances.value = []; // Clear instances if projectId becomes invalid
  }
});

</script>

<style scoped>
/* Scoped styles for Ec2InstanceManagement */
</style>