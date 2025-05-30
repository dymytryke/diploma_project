// filepath: /home/dymytryke/diploma_project/frontend/cmp-frontend/src/services/api.js
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

// Define the base URL of your FastAPI backend
// Make sure this matches where your backend is running.
// For local development, it's often http://localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/';

// Create an instance of axios with default configurations
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json', // Default Content-Type for most requests
  },
});

// Request Interceptor: Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    const token = authStore.getToken;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Optional: Response Interceptor for global error handling (e.g., 401)
/*
apiClient.interceptors.response.use(
  response => response,
  error => {
    const authStore = useAuthStore();
    if (error.response && error.response.status === 401) {
      console.error('API request unauthorized (401). Logging out.');
      authStore.logout();
    }
    return Promise.reject(error);
  }
);
*/

// Export methods for making API calls
export default {
  get(resource, params) { // 'params' here is effectively the Axios config for GET
    return apiClient.get(resource, { params });
  },
  post(resource, data, config) { // Add 'config' argument
    return apiClient.post(resource, data, config); // Pass 'config' to apiClient
  },
  put(resource, data, config) { // Add 'config' argument
    return apiClient.put(resource, data, config); // Pass 'config' to apiClient
  },
  delete(resource, config) { // Add 'config' argument (data might not always be present for delete)
    return apiClient.delete(resource, config); // Pass 'config' to apiClient
  },
  // You might want to add a patch method too if you use it
  patch(resource, data, config) { // Add 'config' argument
    return apiClient.patch(resource, data, config); // Pass 'config' to apiClient
  }
};