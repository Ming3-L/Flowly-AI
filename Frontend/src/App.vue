<template>
  <el-config-provider :locale="locale">
    <div class="app-layout">
      <!-- Navigation Bar (hidden on landing + auth pages) -->
      <nav v-if="!isLandingPage && !isAuthPage" class="app-nav">
        <div class="nav-brand">
          <img class="brand-logo" src="/logo.png" alt="Flowly" />
          <span class="brand-name">Flowly</span>
        </div>

        <el-menu
          mode="horizontal"
          :default-active="activeRoute"
          :router="true"
          class="nav-menu"
          :ellipsis="false"
        >
          <el-menu-item index="/dashboard">首页</el-menu-item>
          <el-menu-item index="/chat">AI 对话</el-menu-item>
          <el-menu-item index="/workflows">工作流</el-menu-item>
          <el-menu-item index="/observability">监控</el-menu-item>
        </el-menu>

        <div class="nav-actions">
          <!-- Authenticated: show user menu -->
          <template v-if="auth.isAuthenticated">
            <el-dropdown trigger="click" @command="handleUserCommand">
              <el-button type="default" size="small" class="user-btn">
                <el-icon><User /></el-icon>
                {{ auth.user?.username }}
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="settings">
                    <el-icon><Setting /></el-icon>
                    设置
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>

          <!-- Guest: show login/register buttons -->
          <template v-else>
            <el-button size="small" @click="$router.push('/login')">登录</el-button>
            <el-button size="small" @click="$router.push('/register')">
              注册
            </el-button>
          </template>

          <el-button
            size="small"
            class="run-btn"
            @click="$router.push('/run')"
          >
            <el-icon><VideoPlay /></el-icon>
            新建运行
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

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const locale = ref(zhCn)

const activeRoute = computed(() => route.path)
const isLandingPage = computed(() => route.path === '/')
const isAuthPage = computed(() => ['/login', '/register'].includes(route.path))

async function handleUserCommand(command: string) {
  if (command === 'logout') {
    await auth.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  } else if (command === 'settings') {
    router.push('/settings')
  }
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
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
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
    color: #000000;
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
    color: #333333;
    height: 52px;
    line-height: 52px;
    padding: 0 16px;

    &.is-active {
      color: #000000;
      border-bottom: 2px solid #000000;
      font-weight: 600;
    }

    &:hover {
      color: #000000;
      background: #f5f5f5;
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

.user-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #e0e0e0;
  background: #ffffff;
  color: #000000;
  font-weight: 500;

  &:hover {
    border-color: #000000;
    background: #f5f5f5;
  }
}

.run-btn {
  background: #000000;
  border-color: #000000;
  color: #ffffff;
  font-weight: 500;

  &:hover {
    background: #333333;
    border-color: #333333;
    color: #ffffff;
  }
}

// ── Page Content ───────────────────────────────────────────────────────────

.app-main {
  flex: 1;
  overflow-y: auto;
  background: #ffffff;
}
</style>
