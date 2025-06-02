// filepath: /home/dymytryke/diploma_project/frontend/cmp-frontend/src/stores/auth.js
import { defineStore } from 'pinia';
import router from '@/router';
import apiService from '@/services/api';

const AUTH_API_ROOT = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    isAuthenticated: JSON.parse(localStorage.getItem('isAuthenticated')) || false,
    user: JSON.parse(localStorage.getItem('user')) || null, // Will now store the full UserOut object
    token: localStorage.getItem('token') || null,
    refreshToken: localStorage.getItem('refreshToken') || null,
    loginError: null,
    signupError: null,
  }),
  getters: {
    isLoggedIn: (state) => state.isAuthenticated,
    currentUser: (state) => state.user,
    getToken: (state) => state.token,
    getLoginError: (state) => state.loginError,
    getSignupError: (state) => state.signupError,
    // Role-based getters
    userRole: (state) => state.user?.role_id || null, // Assuming role_id is the field name from UserOut
    isAdmin: (state) => state.user?.role_id === 'admin', // Adjust 'admin' if your role_id values are different (e.g., UUIDs)
    isDevops: (state) => state.user?.role_id === 'devops',
    isViewer: (state) => state.user?.role_id === 'viewer',
  },
  actions: {
    async fetchCurrentUser() {
      if (this.token) {
        try {
          const response = await apiService.get('/users/me');
          this.user = response.data; // Store the full user object
          localStorage.setItem('user', JSON.stringify(this.user));
          console.log('Current user details fetched:', this.user);
        } catch (error) {
          console.error('Failed to fetch current user:', error.response?.data || error.message);
          // Optionally handle token expiration or other errors here, e.g., by logging out
          if (error.response?.status === 401) {
            this.logout(); // Logout if token is invalid or expired
          }
        }
      }
    },

    async login(credentials) {
      this.loginError = null;
      try {
        const params = new URLSearchParams();
        params.append('username', credentials.username);
        params.append('password', credentials.password);
        params.append('grant_type', 'password');

        const response = await apiService.post(`${AUTH_API_ROOT}/token`, params, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });

        const { access_token, refresh_token, token_type } = response.data;
        if (token_type.toLowerCase() !== 'bearer') throw new Error('Unsupported token type');

        this.token = access_token;
        this.refreshToken = refresh_token;
        this.isAuthenticated = true;

        localStorage.setItem('token', this.token);
        localStorage.setItem('refreshToken', this.refreshToken);
        localStorage.setItem('isAuthenticated', JSON.stringify(this.isAuthenticated));

        await this.fetchCurrentUser(); // Fetch user details after getting token

        console.log('Login successful for:', this.user?.email || credentials.username);
        router.push('/');
        return true;
      } catch (error) {
        console.error('Login failed:', error.response?.data || error.message);
        this.isAuthenticated = false;
        this.user = null;
        this.token = null;
        this.refreshToken = null;
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        localStorage.removeItem('isAuthenticated');

        if (error.response && error.response.data) {
          if (typeof error.response.data.detail === 'string') {
            this.loginError = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail)) {
            this.loginError = error.response.data.detail.map(d => `${d.loc.join('.')} - ${d.msg}`).join('; ');
          } else {
            this.loginError = 'Invalid username or password.';
          }
        } else {
          this.loginError = 'An error occurred during login. Please try again.';
        }
        return false;
      }
    },

    async signup(credentials) {
      this.signupError = null;
      try {
        const response = await apiService.post(`${AUTH_API_ROOT}/signup`, {
          email: credentials.email,
          password: credentials.password,
        });

        const { access_token, refresh_token, token_type } = response.data;
        if (token_type.toLowerCase() !== 'bearer') throw new Error('Unsupported token type');

        this.token = access_token;
        this.refreshToken = refresh_token;
        this.isAuthenticated = true;

        localStorage.setItem('token', this.token);
        localStorage.setItem('refreshToken', this.refreshToken);
        localStorage.setItem('isAuthenticated', JSON.stringify(this.isAuthenticated));

        await this.fetchCurrentUser(); // Fetch user details after getting token

        console.log('Signup successful for:', this.user?.email);
        router.push('/');
        return true;
      } catch (error) {
        console.error('Signup failed:', error.response?.data || error.message);
        this.isAuthenticated = false;
        this.user = null;
        this.token = null;
        this.refreshToken = null;
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        localStorage.removeItem('isAuthenticated');

        if (error.response && error.response.data) {
          if (typeof error.response.data.detail === 'string') {
            this.signupError = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail) && error.response.data.detail[0] && error.response.data.detail[0].msg) {
            this.signupError = error.response.data.detail.map(d => `${d.loc.join('.')} - ${d.msg}`).join('; ');
          } else if (error.response.data.message) {
            this.signupError = error.response.data.message;
          } else {
            this.signupError = 'An error occurred during signup.';
          }
        } else {
          this.signupError = 'An error occurred during signup. Please try again.';
        }
        return false;
      }
    },

    logout() {
      this.isAuthenticated = false;
      this.user = null;
      this.token = null;
      this.refreshToken = null;
      this.loginError = null;
      this.signupError = null;

      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      localStorage.removeItem('isAuthenticated');

      console.log('User logged out');
      router.push('/login');
    },

    // Action to initialize store from localStorage (e.g., on app load)
    async initializeAuth() {
      if (this.token && !this.user) { // If token exists but user details are not loaded
        await this.fetchCurrentUser();
      }
    }
  },
});