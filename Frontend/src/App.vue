<template>
  <el-config-provider :locale="locale">
    <div class="app-layout">
      <!-- Navigation Bar (hidden on landing + auth pages) -->
      <nav v-if="!isLandingPage && !isAuthPage" class="app-nav">
        <div class="nav-brand">
          <img class="brand-logo" :src="isDarkTheme ? '/logow.png' : '/logo.png'" :alt="ui.t('app.brand.name')" />
          <span class="brand-name">{{ ui.t('app.brand.name') }}</span>
        </div>

        <el-menu
          mode="horizontal"
          :default-active="activeRoute"
          :router="true"
          class="nav-menu"
          :ellipsis="false"
        >
          <el-menu-item index="/dashboard">{{ ui.t('app.nav.home') }}</el-menu-item>
          <el-menu-item index="/chat">{{ ui.t('app.nav.chat') }}</el-menu-item>
          <el-menu-item index="/auto-reply">{{ ui.t('app.nav.autoReply', 'AI 自动回复') }}</el-menu-item>
          <el-menu-item index="/workflows">{{ ui.t('app.nav.workflows') }}</el-menu-item>
          <el-menu-item index="/observability">{{ ui.t('app.nav.observability') }}</el-menu-item>
        </el-menu>

        <div class="nav-actions">
          <!-- Theme toggle -->
          <button class="theme-toggle-btn" :title="isDarkTheme ? '切换到浅色' : '切换到深色'" @click="handleToggleTheme">
            <!-- Sun icon (shown in dark mode → click to go light) -->
            <svg v-if="isDarkTheme" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <!-- Moon icon (shown in light mode → click to go dark) -->
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>

          <!-- Authenticated: show user menu -->
          <template v-if="auth.isAuthenticated">
            <el-dropdown trigger="click" @command="handleUserCommand">
              <el-button type="default" size="small" class="user-btn">
                <el-avatar
                  :size="22"
                  :src="auth.user?.avatar_public_url || undefined"
                  class="user-avatar"
                >
                  <el-icon><User /></el-icon>
                </el-avatar>
                {{ auth.user?.nickname || auth.user?.username }}
                <el-tag
                  v-if="auth.user?.is_superuser"
                  size="small"
                  type="danger"
                  effect="plain"
                  class="role-tag"
                >超管</el-tag>
                <el-tag
                  v-else-if="auth.user?.is_staff"
                  size="small"
                  type="warning"
                  effect="plain"
                  class="role-tag"
                >管理员</el-tag>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="settings">
                    <el-icon><Setting /></el-icon>
                    {{ ui.t('app.user.settings') }}
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    {{ ui.t('app.user.logout') }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>

          <!-- Guest: show login/register buttons -->
          <template v-else>
            <el-button size="small" @click="$router.push('/login')">{{ ui.t('app.auth.login') }}</el-button>
            <el-button size="small" @click="$router.push('/register')">
              {{ ui.t('app.auth.register') }}
            </el-button>
          </template>

          <el-button
            size="small"
            class="run-btn"
            @click="$router.push('/run')"
          >
            <el-icon><VideoPlay /></el-icon>
            {{ ui.t('app.nav.newRun') }}
          </el-button>
        </div>
      </nav>

      <!-- Page Content -->
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  User,
  ArrowDown,
  SwitchButton,
  Setting,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAuthStore } from '@/stores/auth'
import { useUiLabelsStore } from '@/stores/uiLabels'
import { themeVersion } from '@/stores/themeStore'
import { toggleTheme } from '@/utils/theme'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiLabelsStore()

const locale = ref(zhCn)

const activeRoute = computed(() => route.path)
const isLandingPage = computed(() => route.path === '/')
const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))
const isDarkTheme = computed(() => {
  void themeVersion.value
  return document.documentElement.classList.contains('theme-dark')
})

async function handleUserCommand(command: string) {
  if (command === 'logout') {
    await auth.logout()
    ElMessage.success(ui.t('app.message.logoutSuccess'))
    router.push('/')
  } else if (command === 'settings') {
    router.push('/settings')
  }
}

function handleToggleTheme() {
  toggleTheme()
}

// Restore session on startup
onMounted(() => {
  auth.fetchCurrentUser()
})
</script>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
}

#app {
  height: 100%;
}
</style>

<style scoped lang="scss">
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

// ── Top Navigation ──────────────────────────────────────────────────────────

.app-nav {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 20px;
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
  flex-shrink: 0;
  gap: 4px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 24px;
  flex-shrink: 0;

  .brand-logo {
    width: 28px;
    height: 28px;
    object-fit: contain;
  }

  .brand-name {
    font-size: 17px;
    font-weight: 700;
    color: var(--app-text);
    letter-spacing: -0.4px;
  }
}

.nav-menu {
  flex: 1;
  border-bottom: none;
  background: transparent;

  :deep(.el-menu-item) {
    font-weight: 500;
    font-size: 14px;
    color: var(--app-text-2);
    height: 52px;
    line-height: 52px;
    padding: 0 16px;

    &.is-active {
      color: var(--app-text);
      border-bottom: 2px solid var(--app-text);
      font-weight: 600;
    }

    &:hover {
      color: var(--app-text);
      background: var(--el-fill-color-light);
    }
  }
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  color: var(--app-text-2);
  cursor: pointer;
  transition: all 0.15s;
  padding: 0;
  flex-shrink: 0;

  &:hover {
    color: var(--app-text);
    border-color: var(--app-text);
    background: var(--el-fill-color-light);
  }

  &:active {
    transform: scale(0.94);
  }
}

.role-tag {
  margin-left: 4px;
  transform: scale(0.92);
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  color: var(--app-text);
  font-weight: 500;

  &:hover {
    border-color: var(--app-text);
    background: var(--el-fill-color-light);
  }
}

.user-avatar {
  flex-shrink: 0;
}

.run-btn {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
  font-weight: 500;

  &:hover {
    background: var(--el-color-primary-light-3);
    border-color: var(--el-color-primary-light-3);
    color: #ffffff;
  }
}

// ── Page Content ───────────────────────────────────────────────────────────

.app-main {
  flex: 1;
  overflow-y: auto;
  background: var(--app-bg);
}
</style>

<!-- Dark mode overrides — non-scoped so they beat scoped styles -->
<style>
html.theme-dark .user-btn {
  background: var(--app-surface) !important;
  border-color: var(--app-border) !important;
  color: var(--app-text) !important;
}
html.theme-dark .run-btn {
  background: var(--app-text) !important;
  border-color: var(--app-text) !important;
  color: var(--app-bg) !important;
  font-weight: 600 !important;
}
</style>
