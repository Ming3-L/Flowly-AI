import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/AuthPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'AuthRegister',
    component: () => import('@/views/AuthPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
  },
  {
    path: '/auto-reply',
    name: 'AutoReply',
    component: () => import('@/views/AutoReplyView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
  },
  {
    path: '/workflows',
    name: 'WorkflowList',
    component: () => import('@/views/WorkflowList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/workflows/:id',
    name: 'WorkflowDetail',
    component: () => import('@/views/WorkflowDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/workflows/new',
    name: 'WorkflowEditorNew',
    component: () => import('@/views/WorkflowEditorView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/workflows/:id/edit',
    name: 'WorkflowEditor',
    component: () => import('@/views/WorkflowEditorView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/workflows/:id/knowledge-base',
    name: 'KnowledgeBase',
    component: () => import('@/views/KnowledgeBaseView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/observability',
    name: 'Observability',
    component: () => import('@/views/ObservabilityView.vue'),
    meta: { requiresAuth: true, requiresStaff: true },
  },
  {
    path: '/admin',
    name: 'AdminConsole',
    component: () => import('@/views/AdminConsoleView.vue'),
    meta: { requiresAuth: true, requiresStaff: true },
  },
  {
    path: '/run',
    name: 'WorkflowRun',
    component: () => import('@/views/WorkflowRunView.vue'),
  },
  {
    path: '/run/:id',
    name: 'WorkflowRunWithId',
    component: () => import('@/views/WorkflowRunView.vue'),
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('@/views/About.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  // Ensure correct routing on GitHub Pages sub-path deployments (base set by Vite `base`).
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// ── Navigation Guard ─────────────────────────────────────────────────────────────

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Attempt to restore session if we have a token but no user yet
  if (auth.accessToken && !auth.user) {
    await auth.fetchCurrentUser()
  }

  // Guest-only routes: redirect authenticated users away from login/register
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return next('/')
  }

  // Protected routes: redirect unauthenticated users to login
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  const staff =
    !!auth.user && (Boolean(auth.user.is_staff) || Boolean(auth.user.is_superuser))
  if (to.meta.requiresStaff && !staff) {
    return next('/dashboard')
  }

  next()
})

export default router
