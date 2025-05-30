import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import ProjectsView from '../views/ProjectsView.vue';
import ProjectDetailView from '../views/ProjectDetailView.vue'; 
import UsersView from '../views/UsersView.vue';
import LoginView from '../views/LoginView.vue';
import SignupView from '../views/SignupView.vue';
import AuditLogView from '../views/AuditLogView.vue'; // <-- IMPORT AuditLogView
import { useAuthStore } from '@/stores/auth';

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { requiresAuth: true } // Home now requires auth
  },
  {
    path: '/projects',
    name: 'projects',
    component: ProjectsView,
    meta: { requiresAuth: true },
  },
  {
    // Ensure the param name matches what ProjectDetailView expects or how you push to it
    path: '/project/:projectId', // Changed from :id to :projectId to be more explicit
    name: 'project-detail',
    component: ProjectDetailView,
    meta: { requiresAuth: true },
    props: true
  },
  {
    path: '/users',
    name: 'users',
    component: UsersView,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/audit', // <-- ADD AuditLog Route
    name: 'AuditLog',
    component: AuditLogView,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { guestOnly: true },
  },
  {
    path: '/signup',
    name: 'signup',
    component: SignupView,
    meta: { guestOnly: true },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// Updated Navigation Guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const isAuthenticated = authStore.isLoggedIn;

  // Initialize auth state if not already done (important for direct navigation/refresh)
  // This might be better handled by an action that runs on app load (e.g., in App.vue's onMounted)
  // but for guards, ensuring the store has attempted to load state is crucial.
  // If initializeAuth is not yet complete, you might need to await it or handle loading state.
  // For simplicity here, we assume initializeAuth has run or isLoggedIn is reliably set.

  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated) {
      next({ name: 'login', query: { redirect: to.fullPath } });
    } else {
      // If route requires admin
      if (to.matched.some(record => record.meta.requiresAdmin)) {
        if (authStore.isAdmin) {
          next(); // User is admin, proceed
        } else {
          // User is authenticated but not admin
          console.warn('Access denied: Route requires admin privileges.');
          next({ name: 'home' }); // Redirect to a safe page
        }
      } else {
        next(); // Route requires auth, user is authenticated, no admin needed
      }
    }
  } else if (to.matched.some(record => record.meta.guestOnly)) {
    if (isAuthenticated) {
      next({ name: 'home' }); // Redirect authenticated users from guest-only pages
    } else {
      next(); // Not authenticated, allow access to guest-only page
    }
  } else {
    next(); // Route does not have specific auth/guest meta, allow access
  }
});

export default router;
